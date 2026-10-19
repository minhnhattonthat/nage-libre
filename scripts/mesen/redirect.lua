-- On the first execution of AT_PC, jump to TO_PC instead (same stack/registers), then play ROUTE2 and screenshot.
-- Params: FROM, ROUTE (reaches AT_PC), ROUTE2 (inputs after the jump), NAME, AT_PC, TO_PC (hex, 24-bit), SHOT_EVERY,
-- MASH (optional: after ROUTE, press this every 20 frames until the jump), LIMIT (frames before giving up, default 20000),
-- FORCE (optional register overrides, L.force).
local function begin()
  L.force(FORCE)
  local at, to, jumped = tonumber(tostring(AT_PC), 16), tonumber(tostring(TO_PC), 16), false
  emu.addMemoryCallback(L.safe(function()
    if jumped then return end
    jumped = true
    emu.setState({ ["cpu.pc"] = to & 0xFFFF, ["cpu.k"] = to >> 16 })
    L.load_route(ROUTE2)
  end), emu.callbackType.exec, at, at, emu.cpuType.snes, emu.memType.snesMemory)
  if ROUTE then L.load_route(ROUTE) end
  local every, start, done, limit = tonumber(SHOT_EVERY or 30), L.frame, false, tonumber(LIMIT or 20000)
  L.on_frame(function(f)
    if (f - start) % every == 0 then L.shot(string.format("shots/%s_%05d.png", NAME, f - start)) end
    if not jumped then
      if f - start > limit then L.fail("AT_PC " .. AT_PC .. " not reached") end
      if MASH and L.route_done() and (f - start) % 20 == 0 then L.press(MASH, 4) end
    end
    if jumped and L.route_done() and not done then
      done = true
      L.shot("shots/" .. NAME .. "_final.png")
      L.save_state(NAME, function() L.finish(0) end)
    end
  end)
end
if FROM then L.load_state(FROM, begin) else begin() end
