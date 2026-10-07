-- Dump MEM[START, START+LEN) on the HIT-th execution of AT_PC.
local mems = { wram = emu.memType.snesWorkRam, vram = emu.memType.snesVideoRam, rom = emu.memType.snesPrgRom }
local frames, adv, want = FRAMES or 1200, ADVANCE or 0, HIT or 1
local function begin()
  local start, hits = L.frame, 0
  emu.addMemoryCallback(L.safe(function()
    hits = hits + 1
    if hits ~= want then return end
    local t = {}
    for i = 0, LEN - 1 do t[#t + 1] = string.char(emu.read(START + i, mems[MEM])) end
    L.write_file("mem/" .. NAME .. ".bin", table.concat(t))
    local s, regs = emu.getState(), {}
    for _, k in ipairs({ "cpu.a", "cpu.x", "cpu.y", "cpu.ps", "cpu.dbr", "cpu.d", "cpu.sp" }) do
      regs[#regs + 1] = string.format("%s=%X", k, s[k])
    end
    L.write_file("mem/" .. NAME .. ".txt", table.concat(regs, " ") .. "\n")
    L.finish(0)
  end), emu.callbackType.exec, AT_PC, AT_PC, emu.cpuType.snes, emu.memType.snesMemory)
  L.on_frame(function(f)
    local n = f - start
    if adv > 0 and n % adv == 0 then L.press("a", 2) end
    if n == frames then L.fail("AT_PC not hit") end
  end)
end
L.load_state(FROM, begin)
