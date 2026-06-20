-- StaticConstructObject_Internal for Dead as Disco (UE 5.7 / CL-29112)
-- Unique function prologue with alloca-heavy register save sequence.
function Register()
    return "48 8B C4 55 41 54 41 55 41 56 41 57 48 8D 68 A1 48 81 EC E0 00 00 00"
end

function OnMatchFound(MatchAddress)
    return MatchAddress
end
