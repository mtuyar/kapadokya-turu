#include "BikeDynamics.h"

namespace
{
	constexpr double G = 9.81;

	// 52/36 + 11-30: tekrarli oranlar elenmis, 18 kullanisli kademe
	constexpr double Ratios[FBikeDynamics::NumGears] = {
		36.0 / 30, 36.0 / 27, 36.0 / 24, 36.0 / 21, 36.0 / 19, 36.0 / 17, 36.0 / 15, 36.0 / 14, 36.0 / 13,
		52.0 / 17, 52.0 / 16, 52.0 / 15, 52.0 / 14, 52.0 / 13, 52.0 / 12, 52.0 / 11.5, 52.0 / 11, 52.0 / 10.5 };

	double CadenceEfficiency(double Rpm)
	{
		// En verimli bant ~90 rpm; cok dusuk ve cok yuksek kadansta guc duser
		const double X = (Rpm - 90.0) / 55.0;
		return FMath::Clamp(FMath::Exp(-X * X), 0.12, 1.0);
	}
}

double FBikeDynamics::GearRatio(int32 Gear)
{
	return Ratios[FMath::Clamp(Gear, 0, NumGears - 1)];
}

double FBikeDynamics::SteadySpeed(const FBikeParams& P, double Power, double Grade, double Crr, double CdA, double Draft)
{
	const double Mass = P.RiderMass + P.BikeMass;
	const double Cos = FMath::Cos(FMath::Atan(Grade));
	const double Sin = FMath::Sin(FMath::Atan(Grade));
	const double Resist = Mass * G * (Crr * Cos + Sin);
	const double K = 0.5 * P.AirDensity * CdA * (1.0 - Draft);
	double V = 8.0;
	for (int32 I = 0; I < 60; ++I)
	{
		// Newton: P*eta = (K v^2 + R) v
		const double F = (K * V * V + Resist) * V - Power * P.Drivetrain;
		const double Df = 3.0 * K * V * V + Resist;
		V = FMath::Clamp(V - F / FMath::Max(Df, 0.5), 0.3, 40.0);
	}
	return V;
}

void FBikeDynamics::UpdateAutoGear(const FBikeInput& Input)
{
	if (State.ShiftTimer > 0.0)
	{
		return;
	}
	int32 Desired = State.Gear;
	if (Input.bAutoGear)
	{
		const double Wanted = Input.Sprint > 0.2 ? 100.0 : 90.0;
		double Best = 1e9;
		for (int32 I = 0; I < NumGears; ++I)
		{
			const double Rpm = State.Speed / (2.0 * UE_DOUBLE_PI * Params.WheelRadius * Ratios[I]) * 60.0;
			// Mevcut vitesi kucuk histerezisle tercih et, gereksiz vites degisimi olmasin
			const double Cost = FMath::Abs(Rpm - Wanted) + (I == State.Gear ? -8.0 : 0.0);
			if (Cost < Best)
			{
				Best = Cost;
				Desired = I;
			}
		}
		Desired = FMath::Clamp(Desired, State.Gear - 1, State.Gear + 1);
	}
	else if (Input.GearDelta != 0)
	{
		Desired = FMath::Clamp(State.Gear + Input.GearDelta, 0, NumGears - 1);
	}
	if (Desired != State.Gear)
	{
		State.Gear = Desired;
		State.ShiftTimer = 0.22;
	}
}

void FBikeDynamics::Step(double Dt, const FBikeInput& Input, const FBikeEnvironment& Env)
{
	constexpr double SubDt = 1.0 / 240.0;
	FBikeInput SubInput = Input;
	UpdateAutoGear(Input);
	SubInput.GearDelta = 0;
	int32 Count = FMath::Clamp(FMath::CeilToInt(Dt / SubDt), 1, 32);
	const double H = Dt / Count;
	for (int32 I = 0; I < Count; ++I)
	{
		SubStep(H, SubInput, Env);
	}
}

void FBikeDynamics::SubStep(double Dt, const FBikeInput& Input, const FBikeEnvironment& Env)
{
	FBikeState& S = State;
	const FBikeParams& P = Params;
	const double Mass = TotalMass();
	const double EffMass = Mass + 2.0 * P.WheelInertia / (P.WheelRadius * P.WheelRadius);
	const double Ratio = GearRatio(S.Gear);
	const double Circ = 2.0 * UE_DOUBLE_PI * P.WheelRadius;
	const double Slope = FMath::Atan(Env.Grade);

	// --- Sporcu ---
	S.Cadence = S.Speed / (Circ * Ratio) * 60.0;
	S.ShiftTimer = FMath::Max(0.0, S.ShiftTimer - Dt);
	const double ShiftCut = S.ShiftTimer > 0.10 ? 0.25 : 1.0;
	double WantPower = Input.Effort * P.CP;
	if (Input.Sprint > 0.0 && S.WPrime > 200.0)
	{
		WantPower = FMath::Lerp(WantPower, P.MaxSprintPower, Input.Sprint);
	}
	// W' bitince esigin altina dusulur
	const double WFrac = S.WPrime / P.WPrimeMax;
	const double Bonk = WFrac < 0.05 ? FMath::Lerp(0.72, 1.0, WFrac / 0.05) : 1.0;
	double Power = WantPower * Bonk * ShiftCut;

	const double CadEff = S.Speed < 3.0 ? 1.0 : CadenceEfficiency(S.Cadence);
	Power *= CadEff;

	if (Power > P.CP)
	{
		S.WPrime = FMath::Max(0.0, S.WPrime - (Power - P.CP) * Dt);
	}
	else
	{
		const double Recover = (P.WPrimeMax - S.WPrime) * (P.CP - Power) / P.WPrimeMax;
		S.WPrime = FMath::Min(P.WPrimeMax, S.WPrime + Recover * Dt * 1.6 * Env.TimeScaleFatigue);
	}
	S.Power = Power;
	const double HRTarget = FMath::Lerp(P.RestingHR + 30.0, P.MaxHR, FMath::Clamp(Power / (P.CP * 1.15), 0.0, 1.0));
	const double HRRate = HRTarget > S.HeartRate ? 0.12 : 0.05;
	S.HeartRate += (HRTarget - S.HeartRate) * FMath::Min(1.0, HRRate * Dt);

	// --- Boyuna kuvvetler ---
	const double VSafe = FMath::Max(S.Speed, 1.0);
	const double DriveForce = FMath::Min(Power * P.Drivetrain / VSafe, P.MaxCrankForceAtWheel * FMath::Clamp(Input.Effort + Input.Sprint, 0.0, 1.0));
	const double TuckBlend = Input.bTuck ? 1.0 : 0.0;
	const double CdA = FMath::Lerp(P.CdAHoods, P.CdATuck, TuckBlend);
	const double Drag = 0.5 * P.AirDensity * CdA * (1.0 - Env.DraftFactor) * S.Speed * S.Speed;
	const double Roll = Env.Crr * Mass * G * FMath::Cos(Slope) * (S.Speed > 0.01 ? 1.0 : 0.0);
	const double Gravity = Mass * G * FMath::Sin(Slope);
	const double CosLean = FMath::Cos(S.Lean);
	// Yatikken frenin kullanabilecegi tutus azalir (surtunme dairesi)
	const double LatUse = FMath::Clamp(FMath::Abs(S.Speed * S.YawRate) / (Env.Mu * G), 0.0, 1.0);
	const double BrakeGrip = FMath::Sqrt(FMath::Max(0.03, 1.0 - LatUse * LatUse)) * Env.Mu * Mass * G * 0.92;
	const double BrakeForce = Input.Brake * BrakeGrip * (S.Speed > 0.01 ? 1.0 : 0.0);

	const double Accel = (DriveForce - Drag - Roll - Gravity - BrakeForce) / EffMass;
	S.Speed = FMath::Clamp(S.Speed + Accel * Dt, Gravity < 0.0 ? -0.2 : -1.2, 42.0);
	if (S.Speed < 0.0 && Gravity <= 0.0 && Input.Effort < 0.01)
	{
		S.Speed = 0.0;
	}

	// --- Enine: istenen yatis -> ters direksiyon -> yatis ---
	const double V = FMath::Max(S.Speed, 0.0);
	const double GripLean = FMath::Atan(Env.Mu);
	const double MaxLean = FMath::Min(FMath::DegreesToRadians(P.MaxLeanDeg), GripLean * 1.08);
	const double LowSpeed = FMath::GetMappedRangeValueClamped(FVector2D(1.0, 4.5), FVector2D(0.15, 1.0), V);
	const double DesiredLean = FMath::Clamp(Input.Lean, -1.0, 1.0) * MaxLean * LowSpeed;

	const double L = P.Wheelbase;
	const double H = P.ComHeight;
	if (V > 1.5)
	{
		// Durum geri beslemesi: yatis hatasi isaretine gore ters yonde gidon baslatir.
		// d2phi = g/h*sin(phi) - v^2/(h L) tan(delta) cos(phi)
		const double Kp = 11.0;
		const double Kd = 6.5;
		const double WantAccel = Kp * (DesiredLean - S.Lean) - Kd * S.LeanRate;
		const double Num = (G / H) * FMath::Sin(S.Lean) - WantAccel;
		const double Den = FMath::Max(V * V / (H * L) * FMath::Max(CosLean, 0.3), 0.2);
		const double DeltaCmd = FMath::Clamp(FMath::Atan(Num / Den), -0.42, 0.42);
		// Gidon ve kol hizi sinirli
		const double MaxRate = 2.8;
		S.Steer += FMath::Clamp(DeltaCmd - S.Steer, -MaxRate * Dt, MaxRate * Dt);
		const double LeanAcc = (G / H) * FMath::Sin(S.Lean) - (V * V / (H * L)) * FMath::Tan(S.Steer) * CosLean;
		S.LeanRate += LeanAcc * Dt;
		S.Lean += S.LeanRate * Dt;
	}
	else
	{
		// Cok dusuk hiz: ayak yerde, bisiklet dogrudan yonlendirilir
		S.Steer += (FMath::Clamp(Input.Lean, -1.0, 1.0) * 0.5 - S.Steer) * FMath::Min(1.0, 6.0 * Dt);
		S.Lean += (0.0 - S.Lean) * FMath::Min(1.0, 5.0 * Dt);
		S.LeanRate = 0.0;
	}
	S.Lean = FMath::Clamp(S.Lean, -1.1, 1.1);

	// --- Yonelim ve tutus ---
	double YawRate = V * FMath::Tan(S.Steer) / L * FMath::Max(CosLean, 0.25);
	const double LatAcc = FMath::Abs(V * YawRate);
	const double Limit = Env.Mu * G;
	if (LatAcc > Limit && V > 1.0)
	{
		const double Over = LatAcc / Limit - 1.0;
		S.SlipAmount = FMath::Min(1.0, S.SlipAmount + (Over * 8.0 + 0.4) * Dt);
		S.GripOverTime += Dt * (1.0 + Over * 3.0);
		YawRate = FMath::Sign(YawRate) * Limit / V;
		S.SlipOffset += FMath::Sign(YawRate) * -1.0 * (LatAcc - Limit) * Dt;
		if (S.GripOverTime > 0.9)
		{
			S.bCrashed = true;
		}
	}
	else
	{
		S.SlipAmount = FMath::Max(0.0, S.SlipAmount - 2.5 * Dt);
		S.GripOverTime = FMath::Max(0.0, S.GripOverTime - 1.5 * Dt);
	}
	// Frenle kilitli on teker de tutusu asar
	if (Input.Brake > 0.97 && LatUse > 0.75 && V > 6.0)
	{
		S.GripOverTime += Dt * 1.2;
	}
	S.SlipOffset *= FMath::Max(0.0, 1.0 - 4.0 * Dt);
	S.YawRate = YawRate;
	S.Heading += YawRate * Dt;

	// --- Kinematik ---
	S.WheelAngle += S.Speed / P.WheelRadius * Dt;
	const double DriveRpm = S.Cadence;
	if (Input.Effort + Input.Sprint > 0.02 && S.Speed > 0.2)
	{
		S.CrankAngle += DriveRpm / 60.0 * 2.0 * UE_DOUBLE_PI * Dt;
	}
}
