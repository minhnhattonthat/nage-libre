-- Aggregate ROM reads (file offsets) and WRAM writes per PC, log VRAM DMAs, dump memories at the end.
local frames, adv, name = FRAMES or 600, ADVANCE or 0, NAME or FROM
local snes, T = emu.cpuType.snes, emu.callbackType
local lastPC, vmadd = 0, 0
local romBy, wramBy = {}, {}
local function bump(t, a)
  local e = t[lastPC]
  if not e then t[lastPC] = { n = 1, lo = a, hi = a }
  else e.n = e.n + 1; if a < e.lo then e.lo = a end; if a > e.hi then e.hi = a end end
end
local function writeAgg(t, rel)
  local f = assert(io.open(L.path(rel), "w")); f:write("pc,n,lo,hi\n")
  for pc, e in pairs(t) do f:write(string.format("%06X,%d,%06X,%06X\n", pc, e.n, e.lo, e.hi)) end
  f:close()
end
local function begin()
  local start = L.frame
  local dma = assert(io.open(L.path("trace/" .. name .. "_dma.csv"), "w"))
  dma:write("frame,pc,ch,bbus,src,size,vmadd\n")
  emu.addMemoryCallback(function(a) lastPC = a end, T.exec, 0, 0xFFFFFF, snes, emu.memType.snesMemory)
  emu.addMemoryCallback(function(a)
    local o, p = L.rom_off(a), L.rom_off(lastPC)
    if o < p or o > p + 3 then bump(romBy, o) end            -- skip the instruction's own operand fetches
  end, T.read, 0, 0x17FFFF, snes, emu.memType.snesPrgRom)
  emu.addMemoryCallback(function(a) bump(wramBy, a) end, T.write, 0, 0x1FFFF, snes, emu.memType.snesWorkRam)
  L.on_reg_write(0x2116, function(a, v) vmadd = (vmadd & 0xFF00) | v end)
  L.on_reg_write(0x2117, function(a, v) vmadd = (vmadd & 0x00FF) | (v << 8) end)
  L.on_reg_write(0x420B, function(a, v)
    local dbg = emu.memType.snesDebug
    for ch = 0, 7 do
      if v & (1 << ch) ~= 0 then
        local b = 0x4300 + ch * 16
        local bbus = emu.read(b + 1, dbg)
        local src = emu.read(b + 2, dbg) | (emu.read(b + 3, dbg) << 8) | (emu.read(b + 4, dbg) << 16)
        local size = emu.read(b + 5, dbg) | (emu.read(b + 6, dbg) << 8)
        dma:write(string.format("%d,%06X,%d,%02X,%06X,%04X,%04X\n", L.frame - start, lastPC, ch, bbus, src, size, vmadd))
      end
    end
  end)
  L.on_frame(function(f)
    local n = f - start
    if adv > 0 and n % adv == 0 then L.press("a", 2) end
    if n % 30 == 0 then L.shot(string.format("shots/%s_t%05d.png", name, n)) end
    if n == frames then
      dma:close()
      writeAgg(romBy, "trace/" .. name .. "_rom.csv")
      writeAgg(wramBy, "trace/" .. name .. "_wram.csv")
      L.dump_mem(emu.memType.snesVideoRam, 0x10000, "mem/" .. name .. "_vram.bin")
      L.dump_mem(emu.memType.snesWorkRam, 0x20000, "mem/" .. name .. "_wram.bin")
      L.dump_mem(emu.memType.snesCgRam, 0x200, "mem/" .. name .. "_cgram.bin")
      L.finish(0)
    end
  end)
end
L.load_state(FROM, begin)
