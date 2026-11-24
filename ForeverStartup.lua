-- Measure from the first addon script, including the bundled gear pages.
local _, private = ...
if type(private) == "table" then
    private.loadStarted = debugprofilestop and debugprofilestop()
    private.heapAtLoad = collectgarbage and collectgarbage("count")
end
