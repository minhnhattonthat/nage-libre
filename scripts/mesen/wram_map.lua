-- Record which 256-byte pages of WRAM bank $7F are written (first writer PC) while playing ROUTE from power-on.
local pages, lastPC = {}, 0
emu.addMemoryCallback(function(a) lastPC = a end, emu.callbackType.exec, 0, 0xFFFFFF, emu.cpuType.snes, emu.memType.snesMemory)
emu.addMemoryCallback(function(a)
  local p = (a >> 8) & 0xFF
  if not pages[p] then pages[p] = lastPC end
end, emu.callbackType.write, 0x10000, 0x1FFFF, emu.cpuType.snes, emu.memType.snesWorkRam)
L.load_route(ROUTE)
local done = false
L.on_frame(function(f)
  if L.route_done() and not done then
    done = true
    local out = assert(io.open(L.path("trace/wram7f_" .. NAME .. ".txt"), "w"))
    for p, pc in pairs(pages) do out:write(string.format("%02X %06X\n", p, pc)) end
    out:close()
    L.shot("shots/wram_" .. NAME .. "_final.png")
    L.finish(0)
  end
end)
