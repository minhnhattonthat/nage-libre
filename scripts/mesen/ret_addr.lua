-- On the first execution of AT_PC, log the long return address on the stack (jsl pushes PB, PCH, PCL).
-- Params: FROM, ROUTE, NAME, AT_PC (hex).
local function begin()
  local pc, done = tonumber(tostring(AT_PC), 16), false
  emu.addMemoryCallback(L.safe(function()
    if done then return end
    done = true
    local s = emu.getState()
    local sp = s["cpu.sp"]
    local mem = emu.memType.snesMemory
    local lo, hi, bank = emu.read(sp + 1, mem), emu.read(sp + 2, mem), emu.read(sp + 3, mem)
    L.write_file("trace/ret_" .. NAME .. ".txt", string.format("frame %d sp=%04X ret=%02X%02X%02X\n", L.frame, sp, bank, hi, lo))
  end), emu.callbackType.exec, pc, pc, emu.cpuType.snes, emu.memType.snesMemory)
  L.load_route(ROUTE)
  L.on_frame(function() if L.route_done() then L.finish(0) end end)
end
if FROM then L.load_state(FROM, begin) else begin() end
