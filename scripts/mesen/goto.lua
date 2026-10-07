-- Play ROUTE, screenshot every SHOT_EVERY frames to shots/<SAVE>_NNNNN.png, save state <SAVE> at the end.
local every = SHOT_EVERY or 60
local function begin()
  local start, saving = L.frame, false
  L.load_route(ROUTE)
  L.on_frame(function(f)
    local n = f - start
    if n % every == 0 then L.shot(string.format("shots/%s_%05d.png", SAVE, n)) end
    if L.route_done() and not saving then
      saving = true
      L.shot("shots/" .. SAVE .. "_final.png")
      L.save_state(SAVE, function() L.finish(0) end)
    end
  end)
end
if FROM then L.load_state(FROM, begin) else begin() end
