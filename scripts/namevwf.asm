; Battle HUD name renderer (asar 1.91; bytes embedded in scripts/namevwf.py, which tests they match this source).
; Replaces the name builder body at 81BA86: given name, a space, then the surname, drawn with the narrow
; proportional font (font/name_glyphs.txt) into the 10-column 2bpp buffer [$06] (0x140 bytes, column c at c*0x20,
; top tile then bottom tile, so row r of a column is byte 2r (+1 for plane 1)).
; In: A/X/Y 16-bit, X = surname table index, Y = given-name table index (pointer table $81AF58, 3 bytes each).
; Font record per code 0x20-0x7F at FONT + (code-0x20)*34: advance, pad, 16 rows x (plane 0, plane 1).
lorom
!FONT = $BFC200
!SPACE = 3                     ; space advance between given name and surname
!PEN = $00
!TMP = $02
!END = $04

org $BFC000
namevwf:
    php
    rep #$30
    pei (!PEN)
    pei (!TMP)
    pei (!END)
    phx
    phy
    ldy #$0140
    lda #$0000
-   dey
    dey
    sta [$06],y
    bne -
    stz !PEN
    pla                        ; given name
    stz !END
    jsr part
    pla                        ; surname
    ldx.w #!SPACE
    stx !END
    jsr part
    pla
    sta !END
    pla
    sta !TMP
    pla
    sta !PEN
    plp
    rtl

part:                          ; A = table index, !END = advance before the first glyph (if any)
    sta !TMP
    asl
    clc
    adc !TMP
    tax
    lda $81AF58,x
    sta $09
    sep #$20
    lda $81AF5A,x
    sta $0B
    rep #$20
    lda [$09]
    cmp #$FFFF
    beq .done
    lda !PEN
    clc
    adc !END
    sta !PEN
.next
    lda [$09]
    cmp #$FFFF
    beq .done
    sec
    sbc #$0020
    asl
    sta !TMP
    asl
    asl
    asl
    asl
    clc
    adc !TMP                   ; (code-0x20)*34
    tax
    jsr glyph
    inc $09
    inc $09
    bra .next
.done
    rts

glyph:                         ; X = font record offset; ORs the glyph in at pixel !PEN, advances !PEN
    lda !PEN
    and #$0007
    sta !TMP                   ; shift
    lda !PEN
    and #$FFF8
    asl
    asl
    tay                        ; column base (pen/8)*0x20
    txa
    clc
    adc #$0020
    sta !END
.byte
    lda !FONT+2,x
    and #$00FF
    xba
    phx
    ldx !TMP
    beq +
-   lsr
    dex
    bne -
+   plx
    sep #$20
    pha                        ; spill into the next column
    xba
    ora [$06],y
    sta [$06],y
    rep #$20
    tya
    clc
    adc #$0020
    tay
    sep #$20
    pla
    ora [$06],y
    sta [$06],y
    rep #$20
    tya
    sec
    sbc #$001F
    tay
    inx
    cpx !END
    bne .byte
    lda !FONT-$20,x            ; advance byte of this record
    and #$00FF
    clc
    adc !PEN
    sta !PEN
    rts
