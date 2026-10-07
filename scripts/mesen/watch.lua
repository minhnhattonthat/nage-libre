-- Raw access log with registers for selected PCs / code range / WRAM range.
-- Note: memory callbacks report CPU addresses (WRAM $7E0000-$7FFFFF, ROM $80xxxx...).
local frames, adv, maxRows = FRAMES or 300, ADVANCE or 0, MAX_ROWS or 200000
local snes, T, M = emu.cpuType.snes, emu.callbackType, emu.memType
local watch = {}
for h in tostring(PCS or ""):gmatch("[^,]+") do watch[tonumber(h, 16)] = true end
local lastPC, rows, start = 0, 0, 0
local out = assert(io.open(L.path("trace/" .. NAME .. "_watch.csv"), "w"))
out:write("frame,pc,kind,addr,value,a,x,y,p,db,d\n")
local function row(kind, addr, value)
  if rows >= maxRows then return end
  rows = rows + 1
  local s = emu.getState()
  out:write(string.format("%d,%06X,%s,%06X,%04X,%04X,%04X,%04X,%02X,%02X,%04X\n", L.frame - start, lastPC, kind,
    addr, value, s["cpu.a"], s["cpu.x"], s["cpu.y"], s["cpu.ps"], s["cpu.dbr"], s["cpu.d"]))
end
local function begin()
  start = L.frame
  emu.addMemoryCallback(function(a)
    lastPC = a
    if CODE_LO and a >= CODE_LO and a <= CODE_HI then row("x", a, 0) end
  end, T.exec, 0, 0xFFFFFF, snes, M.snesMemory)
  if next(watch) then
    emu.addMemoryCallback(function(a, v) if watch[lastPC] then row("r", a, v) end end, T.read, 0, 0xFFFFFF, snes, M.snesMemory)
    emu.addMemoryCallback(function(a, v) if watch[lastPC] then row("w", a, v) end end, T.write, 0, 0xFFFFFF, snes, M.snesMemory)
  end
  if WRAM_LO then
    emu.addMemoryCallback(function(a, v) row("w", a, v) end, T.write, WRAM_LO, WRAM_HI, snes, M.snesWorkRam)
  end
  L.on_frame(function(f)
    local n = f - start
    if adv > 0 and n % adv == 0 then L.press("a", 2) end
    if n == frames then out:close(); L.finish(0) end
  end)
end
L.load_state(FROM, begin)
