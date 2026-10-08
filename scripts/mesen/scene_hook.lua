-- Force a scene at the loader 8380DB (A = scene number) and capture it.
-- Params: FROM, ROUTE (inputs that reach the first loader call), NAME, SCENE (optional), SHOT_EVERY (optional),
--   SHOT_ON (PC, optional): screenshot 6 frames after each new execution (op 06 wait = one shot per text page);
--   AUTO (optional): after the route, press A 8 frames after each SHOT_ON hit; finish when idle for IDLE frames (600).
local log, replaced = {}, false
local want = SCENE and tonumber(SCENE) or nil
local function begin()
  emu.addMemoryCallback(L.safe(function()
    local s = emu.getState()
    log[#log + 1] = string.format("frame %d A=%04X", L.frame, s["cpu.a"])
    if want and not replaced then
      emu.setState({ ["cpu.a"] = want })
      replaced = true
      log[#log + 1] = string.format("  -> replaced with %04X", want)
    end
  end), emu.callbackType.exec, 0x8380DB, 0x8380DB, emu.cpuType.snes, emu.memType.snesMemory)
  local pendingShot, pendingPress, lastHit, lastPress = nil, nil, -100000, -100000
  if SHOT_ON then
    local pc = tonumber(SHOT_ON)
    emu.addMemoryCallback(function()
      if L.frame - lastHit > 2 then
        pendingShot = L.frame + 6
        if AUTO then pendingPress = L.frame + 8 end
      end
      lastHit = L.frame
    end, emu.callbackType.exec, pc, pc, emu.cpuType.snes, emu.memType.snesMemory)
  end
  L.load_route(ROUTE)
  local every, idle, start, done = tonumber(SHOT_EVERY or 0), tonumber(IDLE or 900), L.frame, false
  local routeEnd = nil
  L.on_frame(function(f)
    if every > 0 and (f - start) % every == 0 then L.shot(string.format("shots/%s_%05d.png", NAME, f - start)) end
    if pendingShot and f >= pendingShot then L.shot(string.format("shots/%s_%05d.png", NAME, f - start)); pendingShot = nil end
    if pendingPress and f >= pendingPress and L.route_done() then L.press("a", 4); pendingPress = nil; lastPress = f end
    if L.route_done() and not routeEnd then routeEnd = f end
    if AUTO and routeEnd and f - math.max(lastHit, lastPress, routeEnd) > 120 then   -- keep-alive for other waits
      L.press("a", 4); lastPress = f
    end
    local finished = routeEnd and (not AUTO or f - math.max(lastHit, routeEnd) > idle)
    if finished and not done then
      done = true
      L.write_file("trace/scene_hook_" .. NAME .. ".txt", table.concat(log, "\n") .. "\n")
      L.finish(0)
    end
  end)
end
if FROM then L.load_state(FROM, begin) else begin() end
