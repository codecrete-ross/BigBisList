"""Counted public inventory witnesses for the Forever availability audit."""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from tools.forever_availability import INVENTORY_TYPES


ICY = "https://db.icy-veins.com/wow-forever/items/"
ETERNA = "https://eternadex.com/en/datenbank/items/"
ARMOR_TYPES = ("cloth", "leather", "mail", "plate", "cosmetic", "miscellaneous")
ICY_ARMOR = {
    1: [(f"armor/{material}/head/", None) for material in ARMOR_TYPES],
    3: [(f"armor/{material}/shoulder/", None) for material in ARMOR_TYPES],
    11: [("armor/miscellaneous/finger/", None)], 12: [("armor/miscellaneous/trinket/", None)],
    14: [("armor/shields/", None)],
    23: [("armor/miscellaneous/held-in-off-hand/", None)],
    28: [(f"armor/{name.lower()}s/", name) for name in ("Idol", "Libram", "Totem")],
}
ETERNA_ARMOR = {1: "kopf", 3: "schultern", 11: "finger", 12: "schmuck", 14: "schilde", 23: "nebenhand"}
ETERNA_WEAPONS = set(("einhandaexte zweihandaexte einhandschwerter zweihandschwerter einhandstreitkolben "
                      "zweihandstreitkolben dolche faustwaffen stangenwaffen staebe boegen armbrueste "
                      "schusswaffen wurfwaffen zauberstaebe weitere-waffen").split())
ICY_TOTAL = re.compile(r"Browse all ([\d,]+) items? in the ")
ICY_RANGE = re.compile(r"([\d,]+)[–-]([\d,]+) of ([\d,]+) items")
ETERNA_TOTAL = re.compile(r"([\d,]+) items?, sorted by level")


def count(text: str) -> int:
    return int(text.replace(",", ""))


class CountedCatalog:
    def __init__(self, read, build: str, client_ids: set[int], market_ids: set[int],
                 client_types: dict[int, set[int]] | None = None, client_receipts: tuple = ()):
        self.read = read
        self.build = build
        self.client_ids = client_ids
        self.market_ids = market_ids
        self.client_types = client_types or {}
        self.client_receipts = client_receipts
        self.pages = {}
        self.weapon_groups = None
        self.eterna_weapons = None

    def page(self, url: str):
        from tools.scrape_wowhead import make_soup

        if url not in self.pages:
            raw, receipt = self.read(url)
            self.pages[url] = make_soup(raw.decode("utf-8-sig")), receipt
        return self.pages[url]

    def icy_children(self, url: str) -> dict[str, int]:
        doc, _ = self.page(url)
        match = ICY_TOTAL.search(doc.get_text(" ", strip=True))
        if not match:
            raise ValueError(f"Missing Icy Veins category total at {url}")
        children = {}
        for link in doc.select("a[href]"):
            dest = urljoin(url, link["href"])
            suffix = dest.removeprefix(url)
            label = re.search(r"([\d,]+) items?$", link.get_text(" ", strip=True))
            if label and re.fullmatch(r"[a-z0-9-]+/", suffix):
                if dest in children:
                    raise ValueError(f"Duplicate Icy Veins category at {url}")
                children[dest] = count(label[1])
        if not children or sum(children.values()) != count(match[1]):
            raise ValueError(f"Icy Veins child counts do not reconcile at {url}")
        return children

    def icy_leaf(self, url: str, advertised: int | None = None) -> tuple[list[int], list[dict]]:
        ids, receipts = [], []
        page, last, total = 1, 0, None
        while total is None or last < total:
            doc, receipt = self.page(f"{url}?sort=id&dir=desc&page={page}")
            text = doc.get_text(" ", strip=True)
            match, public_count = ICY_RANGE.search(text), ICY_TOTAL.search(text)
            if not match or not public_count:
                raise ValueError(f"Missing Icy Veins listing counts at {url}")
            start, stop, current_total = map(count, match.groups())
            if (start != last + 1 or stop < start or stop > current_total or count(public_count[1]) != current_total
                    or (advertised is not None and current_total != advertised) or (total is not None and total != current_total)):
                raise ValueError(f"Icy Veins pagination changed at {url}")
            records = []
            for row in doc.select("tbody tr"):
                cells = row.find_all("td", recursive=False)
                key = cells[0].get_text(strip=True) if cells else ""
                link = cells[1].find("a", href=True) if len(cells) > 1 else None
                if not key.isdecimal() or not link or link["href"] != f"/wow-forever/items/{key}":
                    raise ValueError(f"Missing exact item ID at {url}")
                records.append(int(key))
            if len(records) != stop - start + 1:
                raise ValueError(f"Icy Veins page count mismatch at {url}")
            ids.extend(records)
            receipts.append(receipt)
            last, total, page = stop, current_total, page + 1
        if len(set(ids)) != total or (len(receipts) > 1 and ids != sorted(ids, reverse=True)):
            raise ValueError(f"Icy Veins item IDs repeat or are out of order at {url}")
        return ids, receipts

    def icy(self, inventory_type: int) -> dict:
        receipts = []
        if inventory_type in (13, 22):
            parent = ICY + "weapon/"
            if self.weapon_groups is None:
                self.weapon_groups = {url: self.icy_children(url) for url in self.icy_children(parent)}
            receipts.extend(self.pages[url][1] for url in (parent, *self.weapon_groups))
            leaf = "one-hand/" if inventory_type == 13 else "off-hand/"
            groups = [(url, None, total) for children in self.weapon_groups.values() for url, total in children.items()
                      if url.endswith("/" + leaf)]
        else:
            groups = [(ICY + path, subtype, None) for path, subtype in ICY_ARMOR[inventory_type]]
        if not groups:
            raise ValueError("Icy Veins has no counted partition for this equipment type")
        rows = []
        for url, subtype, total in groups:
            ids, pages = self.icy_leaf(url, total)
            receipts.extend(pages)
            rows.extend({"item_id": identifier, **({"subclass": subtype} if subtype else {})} for identifier in ids)
        return self.witness("icyveins", ICY, inventory_type, rows, receipts)

    def eterna_children(self, label: str) -> tuple[dict[str, int], dict]:
        doc, receipt = self.page(ETERNA)
        title = doc.find("h2", string=label)
        section = title.find_parent("section") if title else None
        if section is None:
            raise ValueError(f"Eternadex has no {label} index")
        groups = {}
        for row in section.find_all("li"):
            link = row.find("a", href=True)
            advertised = re.fullmatch(r"[^\d]+ ([\d,]+)(?: Page \d+)*", row.get_text(" ", strip=True))
            url = urljoin(ETERNA, link["href"]) if link else ""
            slug = url.removeprefix(ETERNA).removesuffix("/")
            if not advertised or not re.fullmatch(r"[a-z-]+", slug) or slug in groups:
                raise ValueError(f"Invalid Eternadex {label} category count")
            groups[slug] = count(advertised[1])
        return groups, receipt

    def eterna_leaf(self, slug: str, total: int) -> tuple[list[int], list[dict]]:
        home = ETERNA + slug + "/"
        ids, receipts, pages = [], [], {1}
        page, expected_pages, capacity = 1, 1, 0
        while page <= expected_pages:
            if page not in pages:
                raise ValueError(f"Missing Eternadex page {page} at {home}")
            url = home if page == 1 else home + f"{page}/"
            doc, receipt = self.page(url)
            main = doc.find("main")
            match = ETERNA_TOTAL.search(main.get_text(" ", strip=True)) if main else None
            if not match or total != count(match[1]):
                raise ValueError(f"Eternadex pagination changed at {home}")
            receipts.append(receipt)
            rows = main.select("tbody tr")
            if page == 1:
                capacity = len(rows)
                expected_pages = (total + capacity - 1) // capacity if capacity else 1
            if len(rows) != min(capacity, total - len(ids)):
                raise ValueError(f"Eternadex page count mismatch at {url}")
            for row in rows:
                link = row.select_one("td:first-child a[href]")
                item = re.fullmatch(r"/en/item/([1-9]\d*)/", urlsplit(urljoin(url, link["href"])).path) if link else None
                if not item:
                    raise ValueError(f"Missing exact Eternadex item ID at {url}")
                ids.append(int(item[1]))
            for link in main.select("a[href]"):
                dest = urljoin(url, link["href"])
                numbered = re.fullmatch(re.escape(home) + r"([1-9]\d*)/", dest)
                if numbered:
                    pages.add(int(numbered[1]))
            page += 1
        if len(ids) != total or len(set(ids)) != total or pages != set(range(1, expected_pages + 1)):
            raise ValueError(f"Eternadex item IDs do not reconcile at {home}")
        return ids, receipts

    def eternadex(self, inventory_type: int) -> dict:
        home = ETERNA
        if inventory_type in (13, 22):
            if not self.client_types or not self.client_receipts:
                raise ValueError("Eternadex weapons require exact inventory types from the reviewed client build")
            if self.eterna_weapons is None:
                groups, index = self.eterna_children("Weapons")
                if not ETERNA_WEAPONS <= groups.keys():
                    raise ValueError("Eternadex weapon index is missing equipment categories")
                ids, receipts = [], [index, *self.client_receipts]
                for slug, total in groups.items():
                    listed, pages = self.eterna_leaf(slug, total)
                    ids.extend(listed)
                    receipts.extend(pages)
                if len(ids) != len(set(ids)):
                    raise ValueError("Eternadex item IDs overlap between weapon categories")
                self.eterna_weapons = ids, receipts
            all_ids, receipts = self.eterna_weapons
            # Keep unknown types in both candidate pools until an exact fact resolves them.
            ids = [i for i in all_ids if i not in self.client_types or inventory_type in self.client_types[i]]
        else:
            slug = ETERNA_ARMOR[inventory_type]
            groups, index = self.eterna_children("Armor")
            ids, pages = self.eterna_leaf(slug, groups[slug])
            home += slug + "/"
            receipts = [index, *pages]
        return self.witness("eternadex", home, inventory_type, [{"item_id": i} for i in ids], receipts)

    def witness(self, provider: str, home: str, inventory_type: int, rows: list[dict], receipts: list[dict]) -> dict:
        ids = {row["item_id"] for row in rows}
        if len(ids) != len(rows) or not self.client_ids or not self.market_ids:
            raise ValueError("Counted inventory requires distinct IDs and both reconciliation catalogs")
        slot = INVENTORY_TYPES[inventory_type]
        return {"url": home + f"#inventory-type-{inventory_type}", "provider": provider, "flavor": "forever",
                "page_type": "catalog", "catalog_kind": "counted_listing", "confidence": "catalog_identity_only",
                "fetched_at": max(r["collected_at"] for r in receipts), "client_build": self.build,
                "input_sources": receipts,
                "reconciliation": {"client_matches": len(ids & self.client_ids), "ahledger_matches": len(ids & self.market_ids),
                                   "listing_only_ids": sorted(ids - self.client_ids - self.market_ids)},
                "records": sorted(({**r, "slot": slot} for r in rows), key=lambda r: r["item_id"]), "relationships": [],
                "catalog_coverage": {"slots": ["Idol", "Libram", "Totem"] if inventory_type == 28 else
                                     ["Off Hand"] if inventory_type in (13, 14, 22, 23) else [slot],
                                     "inventory_types": [inventory_type], "qualities": list(range(8)),
                                     "level_min": 1, "level_max": 59, "total": len(rows), "complete": True},
                "attribution": [{"credit": "Icy Veins (Vedatis S.A.S.)" if provider == "icyveins" else "Eternadex", "source": home}]}
