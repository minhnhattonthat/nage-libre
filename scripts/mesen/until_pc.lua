-- Debug warp: mash MASH (default "a") every EVERY frames until the CPU executes AT_PC, then play ROUTE2,
-- screenshot every SHOT_EVERY frames and save state SAVE. Robust to text-speed changes, unlike fixed routes.
-- Params: FROM, AT_PC (hex, 24-bit), MASH, EVERY (default 20), LIMIT (frames, default 20000), ROUTE2, SAVE,
-- SHOT_EVERY (default 30), POKE ("7E1234=12,..." 8-bit writes done when AT_PC is hit), FORCE (L.force).
local function begin()
  L.force(FORCE)
  local at, every, limit = tonumber(tostring(AT_PC), 16), tonumber(EVERY or 20), tonumber(LIMIT or 20000)
  local mash, hit, hitFrame, done, start = tostring(MASH or "a"), false, nil, false, L.frame
  emu.addMemoryCallback(L.safe(function()
    if hit then return end
    hit, hitFrame = true, L.frame
    for addr, v in tostring(POKE or ""):gmatch("(%x+)=(%x+)") do
      emu.write(tonumber(addr, 16), tonumber(v, 16), emu.memType.snesMemory)
    end
    if ROUTE2 then L.load_route(ROUTE2) end
  end), emu.callbackType.exec, at, at, emu.cpuType.snes, emu.memType.snesMemory)
  L.on_frame(function(f)
    local n = f - start
    if not hit then
      if n > limit then L.shot("shots/" .. SAVE .. "_nohit.png"); L.fail("AT_PC " .. AT_PC .. " not reached") end
      if L.route_done() and n % every == 0 then L.press(mash, 4) end
      return
    end
    local m = f - hitFrame
    if m % tonumber(SHOT_EVERY or 30) == 0 then L.shot(string.format("shots/%s_%05d.png", SAVE, m)) end
    if L.route_done() and not done then
      done = true
      L.shot("shots/" .. SAVE .. "_final.png")
      L.save_state(SAVE, function() L.finish(0) end)
    end
  end)
end
if FROM then L.load_state(FROM, begin) else begin() end
