-- Play ROUTE, screenshot every SHOT_EVERY frames to shots/<SAVE>_NNNNN.png, save state <SAVE> at the end.
-- CHEATS: optional comma-separated Pro Action Replay codes (e.g. "7E10CCFF,7E10D163").
-- FORCE: optional register overrides "PC:reg=hex,..." (L.force), e.g. "828C2E:a=0" offers Rest? to a lone member.
local every = SHOT_EVERY or 60
local function begin()
  for code in tostring(CHEATS or ""):gmatch("[^,]+") do emu.addCheat(emu.cheatType.snesProActionReplay, code) end
  L.force(FORCE)
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
