-- GNatives global variable for Dead as Disco (UE 5.7 / CL-29112)
-- Pattern finds the GNatives initialisation helper function.
-- The "MOV [GNatives], RAX" instruction is at offset 0x15 from pattern start
-- (7-byte instruction: 48 89 05 [4-byte RIP-relative offset]).
-- Adapted from Far Far West UE5.7 signature by the UE4SS community.
function Register()
    return "48 8D 05 ?? ?? ?? ?? 48 39 05 ?? ?? ?? ?? 48 8D 05 ?? ?? ?? ?? 48 89 05 ?? ?? ?? ?? 74 ?? C7 05 ?? ?? ?? ?? 00 00 00 00 C3"
end

function OnMatchFound(MatchAddress)
    local movInstr = MatchAddress + 0x15
    local nextInstr = movInstr + 7
    local offset = DerefToInt32(movInstr + 3)
    return nextInstr + offset
end
