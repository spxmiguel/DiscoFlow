-- FUObjectHashTables::Get() for Dead as Disco (UE 5.7 / CL-29112)
-- UE4SS logs this address but does not store it, so any valid code
-- address satisfies the scan. We anchor on FName_Constructor (unique hit).
function Register()
    return "40 53 48 83 EC 20 48 8B DA 48 85 D2 74 2B E8 5D 6E 3D 00"
end

function OnMatchFound(MatchAddress)
    return MatchAddress
end
