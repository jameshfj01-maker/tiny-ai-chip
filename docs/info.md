<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This project is a tiny AI accelerator. It multiplies two 2x2 matrices of signed 8-bit integers (int8),
C = A x B, using a 2x2 systolic array.

The array has four MAC (multiply-accumulate) units. Each MAC keeps one element of C and adds one
product a * b to it per beat. Values of A move one MAC to the right per beat and values of B move
one MAC down per beat, so each value read from the registers is reused by two MACs.

The MACs are bit-serial to save area: instead of a full 8x8 multiplier, each MAC has one 18-bit
adder and handles one bit of b per clock, adding (a << i) when bit i of b is 1. The sign bit of b
has weight -128 in two's complement, so for bit 7 the MAC subtracts instead of adding.
One beat is 8 clocks.

```
          B col 0     B col 1
             |           |
  A row 0 -> [MAC] ----> [MAC]
             |           |
  A row 1 -> [MAC] ----> [MAC]
```

A small controller feeds A and B into the array with a one clock skew per row and column, so that
matching values meet in the right MAC. One matrix product takes 4 beats = 32 clocks.

Each element of C is 18 bits wide (signed), which is enough for the worst case
(-128 * -128 + -128 * -128 = 32768). It is read out as 3 bytes.

The WRITE and START inputs pass through 2 flip-flop synchronizers and act on their rising edge only.

## How to test

1. Reset the design.
2. Write the 8 input bytes. For each byte: put the value on `DATA_IN[7:0]` (two's complement),
   put the address on `ADDR[3:0]`, then raise `WRITE` for at least 3 clocks and lower it again
   for at least 3 clocks.

   | ADDR | 0   | 1   | 2   | 3   | 4   | 5   | 6   | 7   |
   |------|-----|-----|-----|-----|-----|-----|-----|-----|
   | data | A00 | A01 | A10 | A11 | B00 | B01 | B10 | B11 |

3. Raise `START` for at least 3 clocks, then lower it. `DONE` goes high about 36 clocks later and
   stays high until the next start.
4. Read the result. Put `{cell, byte}` on `ADDR[3:0]` and read `RESULT[7:0]`.
   - cell (ADDR[3:2]): 0 = C00, 1 = C01, 2 = C10, 3 = C11
   - byte (ADDR[1:0]): 0 = bits 7..0, 1 = bits 15..8, 2 = bits 17..16 sign extended to 8 bits, 3 = always 0

   Join the 3 bytes into a 24-bit two's complement number.

Example: A = [[1, 2], [3, 4]], B = [[5, 6], [7, 8]] gives C = [[19, 22], [43, 50]].

Writes and starts are ignored while the array is computing.

A MicroPython test script for the Tiny Tapeout demo board is in `demoboard/tiny_ai_chip.py`
(run `import tiny_ai_chip; tiny_ai_chip.main()` on the board). See `demoboard/README.md`.

## External hardware

None. The Tiny Tapeout demo board (RP2040) can drive the inputs and read the outputs.
