#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "KapadokyaGameMode.generated.h"

class AKapadokyaRace;
class AKapadokyaWorld;

UCLASS()
class KAPADOKYATURU_API AKapadokyaGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	AKapadokyaGameMode();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	AKapadokyaWorld* GetKapadokyaWorld() const { return World; }

private:
	UPROPERTY() TObjectPtr<AKapadokyaWorld> World;

	UPROPERTY() TObjectPtr<AKapadokyaRace> Race;
	TArray<double> RaceShotTimes;
	int32 RaceShotIndex = 0;
	bool bMenuShotDone = false;
	double ProfileAt = -1.0;
	double CsvAt = -1.0;
	int32 SkyProbeIndex = 0;
	double SkyProbeTimer = 0.0;
	bool bHitchLog = false;
	double HitchIgnore = 0.0;
	double HitchClock = 0.0;
	TArray<float> HitchFrames;
	TArray<double> ShotList;
	FString ShotTag = TEXT("shot");
	int32 ShotIndex = -1;
	double ShotTimer = 0.0;
	double FpsSum = 0.0;
	int32 FpsFrames = 0;
};
