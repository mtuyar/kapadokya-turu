#pragma once
#include "CoreMinimal.h"

/**
 * Bisikletin motordan bagimsiz fizik modeli. SI birimleri kullanir.
 *
 * Boyuna: pedal gucu, aerodinamik direnc (draft dahil), yuvarlanma, egim, fren.
 * Enine: ters sarkac + on tekerlek kontrolu. Oyuncu istenen yatis acisini verir,
 *        denetleyici gercek bisikletteki gibi once ters direksiyon yaparak yatisi baslatir.
 * Sporcu: kritik guc (CP) ve W' anaerobik rezervi (Skiba denge modeli), nabiz, kadans verimi.
 */
struct KAPADOKYATURU_API FBikeParams
{
	double RiderMass = 72.0;
	double BikeMass = 7.8;
	double WheelRadius = 0.340;
	double WheelInertia = 0.13;       // tek tekerlek, kg m^2
	double Wheelbase = 0.99;
	double ComHeight = 1.05;
	double CdAHoods = 0.34;
	double CdATuck = 0.24;
	double AirDensity = 1.03;         // ~1100 m rakim (Kapadokya)
	double Drivetrain = 0.975;
	double CP = 310.0;                // Kritik guc, W
	double WPrimeMax = 21000.0;       // Anaerobik rezerv, J
	double MaxSprintPower = 1050.0;
	double MaxCrankForceAtWheel = 1500.0;
	double MaxLeanDeg = 46.0;
	double RestingHR = 62.0;
	double MaxHR = 192.0;
};

struct KAPADOKYATURU_API FBikeInput
{
	double Effort = 0.0;   // 0..1, CP'ye gore; 1 = esik
	double Sprint = 0.0;   // 0..1, Effort uzerine eklenir
	double Brake = 0.0;    // 0..1
	double Lean = 0.0;     // -1..1, istenen yatis (saga +)
	bool bTuck = false;
	int32 GearDelta = 0;   // elle vites
	bool bAutoGear = true;
};

struct KAPADOKYATURU_API FBikeEnvironment
{
	double Grade = 0.0;    // egim orani (0.08 = %8)
	double Mu = 0.85;      // lastik surtunmesi
	double Crr = 0.004;    // yuvarlanma katsayisi
	double DraftFactor = 0.0;  // 0..0.45 hava direnci azalmasi
	double TimeScaleFatigue = 1.0;
};

struct KAPADOKYATURU_API FBikeState
{
	double Speed = 0.0;          // m/s
	double Heading = 0.0;        // rad, +Y'ye dogru pozitif (UE saga donus)
	double YawRate = 0.0;        // rad/s
	double Lean = 0.0;           // rad, saga +
	double LeanRate = 0.0;
	double Steer = 0.0;          // rad, gidon acisi
	double SlipOffset = 0.0;     // yanal kayma hizi, m/s
	double SlipAmount = 0.0;     // 0..1, lastik sinirini asma
	double CrankAngle = 0.0;     // rad
	double WheelAngle = 0.0;     // rad
	double Cadence = 0.0;        // rpm
	double Power = 0.0;          // W
	double WPrime = 21000.0;     // J
	double HeartRate = 95.0;
	double GripOverTime = 0.0;   // saniye, dusme tespiti
	double ShiftTimer = 0.0;
	int32 Gear = 9;
	bool bCrashed = false;
};

class KAPADOKYATURU_API FBikeDynamics
{
public:
	static constexpr int32 NumGears = 18;

	FBikeParams Params;
	FBikeState State;

	/** Sabit adimda ilerler; dt buyukse icinde bolunur. */
	void Step(double Dt, const FBikeInput& Input, const FBikeEnvironment& Env);

	static double GearRatio(int32 Gear);
	double TotalMass() const { return Params.RiderMass + Params.BikeMass; }
	/** Verilen egim/guc icin denge hizi (test ve YZ hedefi icin). */
	static double SteadySpeed(const FBikeParams& P, double Power, double Grade, double Crr, double CdA, double Draft);

private:
	void SubStep(double Dt, const FBikeInput& Input, const FBikeEnvironment& Env);
	void UpdateAutoGear(const FBikeInput& Input);
};
