using UnrealBuildTool;
public class KapadokyaTuruTarget : TargetRules
{
	public KapadokyaTuruTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("KapadokyaTuru");
	}
}
