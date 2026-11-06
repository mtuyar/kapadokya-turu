#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "KapadokyaRace.generated.h"

class AKapadokyaRider;
class AKapadokyaWorld;
class UAudioComponent;
class USoundBase;

UENUM()
enum class EKRaceState : uint8 { Menu, Countdown, Racing, Results, Paused };

struct FKMenuItem
{
	FString Label;
	TArray<FString> Options;
	int32 Value = 0;
};

/** Yaris akisi, siralama, draft, puanlar ve menu durumu. */
UCLASS()
class KAPADOKYATURU_API AKapadokyaRace : public AActor
{
	GENERATED_BODY()
public:
	AKapadokyaRace();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	void Setup(AKapadokyaWorld* InWorld);

	// Menu girdileri
	void MenuMove(int32 Delta);
	void MenuChange(int32 Delta);
	void MenuConfirm();
	void TogglePause();

	EKRaceState State = EKRaceState::Menu;
	TArray<FKMenuItem> Menu;
	int32 MenuIndex = 0;
	bool bPausedMenu = false;

	UPROPERTY() TArray<TObjectPtr<AKapadokyaRider>> Riders;
	UPROPERTY() TObjectPtr<AKapadokyaRider> Player;

	double RaceTime = 0.0;
	double Countdown = 0.0;
	int32 Laps = 1;
	double RaceDistance = 0.0;
	FString Banner;
	double BannerTimer = 0.0;
	FString ZoneTitle;
	double ZoneTimer = 0.0;
	double MenuClock = 0.0;

	double KomS = 0.0;
	double StartLineS = 36000.0;

private:
	void BuildMenu(bool bPause);
	void ApplySettings();
	void StartRace();
	void TickRiders(float Dt);
	void UpdatePack(float Dt);
	void UpdateOrder();
	void AwardPoints();
	void Finish(AKapadokyaRider* Rider);
	void WriteTelemetry(float Dt);
	// Eglence modu: cay turbosu, yola sacilan fici ve kasalar, abartili kaza
	void SpawnFun();
	void UpdateFun(float Dt);
	struct FKFunItem
	{
		double S = 0.0;
		double Lat = 0.0;
		int32 Type = 0; // 0 cay, 1 fici, 2 kasa
		FVector Home = FVector::ZeroVector;
		FVector Vel = FVector::ZeroVector;
		FVector Spin = FVector::ZeroVector;
		double FlyTime = -1.0;
		double Hidden = 0.0;
	};
	TArray<FKFunItem> FunItems;
	UPROPERTY() TArray<TObjectPtr<class UStaticMeshComponent>> FunMeshes;
	bool bFunMode = true;
	bool bPlayerWasCrashed = false;
	double TurboTime = 0.0;
	double SlowTime = 0.0;
	int32 JokeIndex = 0;
	void Show(const FString& Text, double Seconds = 3.0);

	UPROPERTY() TObjectPtr<AKapadokyaWorld> World;
	UPROPERTY() TObjectPtr<UAudioComponent> Music;
	UPROPERTY() TObjectPtr<UAudioComponent> Crowd;
	UPROPERTY() TObjectPtr<USoundBase> SndBeep;
	UPROPERTY() TObjectPtr<USoundBase> SndGo;
	UPROPERTY() TObjectPtr<USoundBase> SndFanfare;

	TArray<double> PrevS;
	TArray<int32> KomAwarded;
	TArray<int32> SprintAwarded;
	int32 LastBeep = -1;
	int32 LastZone = -1;
	double FinishDelay = -1.0;
	int32 FinishedCount = 0;
	double TelemetryClock = 0.0;
	double QuitAfter = -1.0;
	TArray<double> JumpPoints;
	int32 JumpIndex = 0;
	double JumpEvery = 30.0;
	void UpdateJumps();
	FString TelemetryPath;
	bool bAuto = false;
	int32 Difficulty = 1;
	bool bAssist = true;
	int32 RiderCount = 12;
};

UCLASS()
class KAPADOKYATURU_API AKapadokyaPC : public APlayerController
{
	GENERATED_BODY()
public:
	AKapadokyaPC();
	virtual void SetupInputComponent() override;
	AKapadokyaRace* Race() const;
};
