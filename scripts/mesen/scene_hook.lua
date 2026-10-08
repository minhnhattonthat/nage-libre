-- Force a scene at the loader 8380DB (A = scene number) and capture it.
-- Params: FROM, ROUTE (inputs that reach the first loader call), NAME, SCENE (optional), SHOT_EVERY (optional),
--   SHOT_ON (PC, optional): screenshot 6 frames after each new execution (op 06 wait = one shot per text page);
--   AUTO (optional): after the route, press A 8 frames after each SHOT_ON hit; finish when idle for IDLE frames (900).
--   TEXTPIX (optional): log per frame the count of white text pixels in the bottom box -> trace/textpix_NAME.txt.
--   Flags are numbers; 0 means off (Lua treats 0 as true, so they are parsed explicitly).
local log, replaced = {}, false
local want = SCENE and tonumber(SCENE) or nil
local function flag(v) return v ~= nil and v ~= 0 and v ~= "0" end
local auto, textpix = flag(AUTO), flag(TEXTPIX)
local pix = {}
local function count_text()        -- white glyph pixels inside the bottom dialogue box (x 12-243, y 168-213)
  local buf = emu.getScreenBuffer()
  local w = (#buf >= 512 * 478) and 512 or 256
  local k, n = w // 256, 0
  for y = 168, 213 do
    local row = y * k * w
    for x = 12, 243 do
      local c = buf[row + x * k + 1]
      if ((c >> 16) & 255) > 200 and ((c >> 8) & 255) > 200 and (c & 255) > 200 then n = n + 1 end
    end
  end
  return n
end
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
  -- typing printers 80F533 / 80F5B0: track whether a page is typing (keep-alive presses wait for it, like a player
  -- who reads before pressing; A held would fast-forward typing). PRINTLOG logs "S <frame> <string address>" at
  -- start and "E <frame>" at the FFFF end: a start without an end before the next start = a page cut off mid-typing.
  local printing, printStart, printlog = false, 0, flag(PRINTLOG)
  for _, pc in ipairs({ 0x80F53F, 0x80F5BC }) do
    emu.addMemoryCallback(function()
      printing, printStart = true, L.frame
      if printlog then
        local a = emu.read16(0x09, emu.memType.snesMemory) + emu.read(0x0B, emu.memType.snesMemory) * 0x10000
        log[#log + 1] = string.format("S %d %06X", L.frame, a)
      end
    end, emu.callbackType.exec, pc, pc, emu.cpuType.snes, emu.memType.snesMemory)
  end
  for _, pc in ipairs({ 0x80F597, 0x80F5FA }) do
    emu.addMemoryCallback(function()
      printing = false
      if printlog then log[#log + 1] = string.format("E %d", L.frame) end
    end, emu.callbackType.exec, pc, pc, emu.cpuType.snes, emu.memType.snesMemory)
  end
  local pendingShot, pendingPress, lastHit, lastPress = nil, nil, -100000, -100000
  if SHOT_ON then
    local pc = tonumber(SHOT_ON)
    emu.addMemoryCallback(function()
      if L.frame - lastHit > 2 then
        pendingShot = L.frame + 6
        if auto then pendingPress = L.frame + 8 end
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
    if textpix and routeEnd then pix[#pix + 1] = (f - start) .. " " .. count_text() end
    if auto and not (printing and f - printStart < 600) and routeEnd and f - math.max(lastHit, lastPress, routeEnd) > 120 then   -- keep-alive for other waits
      L.press("a", 4); lastPress = f
    end
    local finished = routeEnd and (not auto or f - math.max(lastHit, routeEnd) > idle)
    if finished and not done then
      done = true
      L.write_file("trace/scene_hook_" .. NAME .. ".txt", table.concat(log, "\n") .. "\n")
      if textpix then L.write_file("trace/textpix_" .. NAME .. ".txt", table.concat(pix, "\n") .. "\n") end
      L.finish(0)
    end
  end)
end
if FROM then L.load_state(FROM, begin) else begin() end
