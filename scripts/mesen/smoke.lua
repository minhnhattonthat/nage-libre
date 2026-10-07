-- lib.lua self-check: L.rom_off maps ROM read callbacks to file offsets; save then load restores the frame.
local reads, maxRom = 0, 0
emu.addMemoryCallback(function(a) reads = reads + 1; a = L.rom_off(a); if a > maxRom then maxRom = a end end,
  emu.callbackType.read, 0, 0x17FFFF, emu.cpuType.snes, emu.memType.snesPrgRom)
L.press("-", 200)
local loading = false
L.on_frame(function(f)
  if f == 120 then L.save_state("smoke") end
  if f == 160 and not loading then
    loading = true
    L.load_state("smoke", function()
      L.shot("shots/smoke.png")
      L.write_file("trace/smoke.txt", string.format("reads=%d maxRom=%d loadedFrame=%d\n",
        reads, maxRom, emu.getState()["ppu.frameCount"]))
      L.finish(0)
    end)
  end
end)
