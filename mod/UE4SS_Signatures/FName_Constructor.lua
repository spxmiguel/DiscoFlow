-- FName::FName(wchar_t*, EFindName) for Dead as Disco (UE 5.7 / CL-29112)
-- Unique prologue bytes at the function entry point.
function Register()
    return "40 53 48 83 EC 20 48 8B DA 48 85 D2 74 2B E8 5D 6E 3D 00"
end

function OnMatchFound(MatchAddress)
    return MatchAddress
end
