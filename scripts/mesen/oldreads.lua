-- Count reads of the ORIGINAL system block (ROM 0x38077-0x38B3E) while playing ROUTE from FROM; first reader PC.
-- Params: FROM (state, optional), ROUTE (abs path), NAME, CHEATS (optional PAR codes, comma-separated).
local n, first, lastPC = 0, nil, 0
local function begin()
  for code in tostring(CHEATS or ""):gmatch("[^,]+") do emu.addCheat(emu.cheatType.snesProActionReplay, code) end
  emu.addMemoryCallback(function(a) lastPC = a end, emu.callbackType.exec, 0, 0xFFFFFF, emu.cpuType.snes, emu.memType.snesMemory)
  emu.addMemoryCallback(function(a) n = n + 1; if not first then first = lastPC end end,
    emu.callbackType.read, 0x38077, 0x38B3E, emu.cpuType.snes, emu.memType.snesPrgRom)
  L.load_route(ROUTE)
  local done = false
  L.on_frame(function()
    if L.route_done() and not done then
      done = true
      L.write_file("trace/oldreads_" .. NAME .. ".txt", string.format("%d %06X\n", n, first or 0))
      L.finish(0)
    end
  end)
end
if FROM then L.load_state(FROM, begin) else begin() end
