#include "BikeDynamics.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	double Settle(double Effort, double Grade, double Crr, bool bTuck = false, double Draft = 0.0, double Seconds = 240.0)
	{
		FBikeDynamics B;
		B.Params.CP = 300.0;
		B.State.Speed = 8.0;
		B.State.WPrime = B.Params.WPrimeMax;
		FBikeInput In;
		In.Effort = Effort;
		In.bTuck = bTuck;
		FBikeEnvironment Env;
		Env.Grade = Grade;
		Env.Crr = Crr;
		Env.DraftFactor = Draft;
		for (int32 I = 0; I < int32(Seconds * 60); ++I)
		{
			B.Step(1.0 / 60.0, In, Env);
		}
		return B.State.Speed;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBikeSpeedTest, "Kapadokya.Bike.GercekciHizlar",
	EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext)
bool FBikeSpeedTest::RunTest(const FString&)
{
	const double FlatKmh = Settle(1.0, 0.0, 0.004) * 3.6;
	const double DraftKmh = Settle(1.0, 0.0, 0.004, false, 0.35) * 3.6;
	const double ClimbKmh = Settle(1.0, 0.08, 0.004) * 3.6;
	const double CobbleKmh = Settle(1.0, 0.0, 0.012) * 3.6;
	const double DescentKmh = Settle(0.0, -0.08, 0.004, true) * 3.6;
	{ const FString Line = FString::Printf(TEXT("300W duz %.1f, draft %.1f, %%8 tirmanis %.1f, arnavut %.1f, %%8 inis tuck %.1f km/s"), FlatKmh, DraftKmh, ClimbKmh, CobbleKmh, DescentKmh); AddInfo(Line); UE_LOG(LogTemp, Display, TEXT("BIKETEST %s"), *Line); }
	// Beklenen bantlar: yayinlanmis gucbisiklet hesaplari, 1100 m rakim
	TestTrue(TEXT("Duz 300 W: 38-46 km/s"), FlatKmh > 38 && FlatKmh < 46);
	TestTrue(TEXT("Draft daha hizli"), DraftKmh > FlatKmh + 4);
	TestTrue(TEXT("%8 tirmanis: 14-20 km/s"), ClimbKmh > 14 && ClimbKmh < 20);
	TestTrue(TEXT("Arnavut daha yavas"), CobbleKmh < FlatKmh - 2);
	TestTrue(TEXT("%8 inis: 60-85 km/s"), DescentKmh > 60 && DescentKmh < 85);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBikeCountersteerTest, "Kapadokya.Bike.TersDireksiyon",
	EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext)
bool FBikeCountersteerTest::RunTest(const FString&)
{
	FBikeDynamics B;
	B.State.Speed = 12.0;
	FBikeInput In;
	In.Effort = 0.7;
	In.Lean = 0.5;
	FBikeEnvironment Env;
	double FirstSteerSign = 0.0;
	for (int32 I = 0; I < 180; ++I)
	{
		B.Step(1.0 / 60.0, In, Env);
		if (I == 3)
		{
			FirstSteerSign = B.State.Steer;
		}
	}
	{ const FString Line = FString::Printf(TEXT("ilk gidon %.3f, 3 sn sonra yatis %.1f derece, gidon %.3f, yaw %.3f"), FirstSteerSign, FMath::RadiansToDegrees(B.State.Lean), B.State.Steer, B.State.YawRate); AddInfo(Line); UE_LOG(LogTemp, Display, TEXT("BIKETEST %s"), *Line); }
	TestTrue(TEXT("Saga yatmak icin once sola gidon"), FirstSteerSign < 0.0);
	TestTrue(TEXT("Yatis saga yerlesir"), B.State.Lean > 0.1 && B.State.Lean < 0.6);
	TestTrue(TEXT("Saga doner"), B.State.YawRate > 0.0);
	TestFalse(TEXT("Dusmez"), B.State.bCrashed);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBikeWPrimeTest, "Kapadokya.Bike.AnaerobikRezerv",
	EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext)
bool FBikeWPrimeTest::RunTest(const FString&)
{
	FBikeDynamics B;
	B.State.Speed = 12.0;
	FBikeInput In;
	In.Effort = 1.0;
	In.Sprint = 1.0;
	FBikeEnvironment Env;
	double T = 0.0;
	while (B.State.WPrime > 500.0 && T < 300.0)
	{
		B.Step(1.0 / 60.0, In, Env);
		T += 1.0 / 60.0;
	}
	{ const FString Line = FString::Printf(TEXT("tam sprint %.1f sn, son guc %.0f W, nabiz %.0f"), T, B.State.Power, B.State.HeartRate); AddInfo(Line); UE_LOG(LogTemp, Display, TEXT("BIKETEST %s"), *Line); }
	TestTrue(TEXT("Tam sprint 15-120 sn surer"), T > 15.0 && T < 120.0);
	const double Spent = B.State.WPrime;
	In.Sprint = 0.0;
	In.Effort = 0.5;
	for (int32 I = 0; I < 60 * 60; ++I)
	{
		B.Step(1.0 / 60.0, In, Env);
	}
	TestTrue(TEXT("Toparlanir"), B.State.WPrime > Spent + 1000.0);
	return true;
}

#endif
