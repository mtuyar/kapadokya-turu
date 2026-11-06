#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KapadokyaWorld.generated.h"

class UDirectionalLightComponent;
class USkyLightComponent;
class USkyAtmosphereComponent;
class UExponentialHeightFogComponent;
class UVolumetricCloudComponent;
class UPostProcessComponent;

UENUM()
enum class EKTimeOfDay : uint8 { Dawn, Noon, Sunset };

/** Haritanin tamami veriden kurulur: arazi, yol, yerlesimler, gokyuzu. */
UCLASS()
class KAPADOKYATURU_API AKapadokyaWorld : public AActor
{
	GENERATED_BODY()
public:
	AKapadokyaWorld();
	virtual void BeginPlay() override;

	void ApplyTimeOfDay(EKTimeOfDay Time);
	/** 0 Dusuk, 1 Orta, 2 Yuksek, 3 Sinematik. Oyun icinde degisebilir. */
	void ApplyQuality(int32 Level);
	EKTimeOfDay GetTimeOfDay() const { return TimeOfDay; }
	int32 GetQuality() const { return Quality; }

private:
	void BuildStatic();
	void BuildPlacements();
	void ApplySky(float SunYaw);
	UPROPERTY() TArray<TObjectPtr<class UHierarchicalInstancedStaticMeshComponent>> SmallCasters;

	UPROPERTY() TObjectPtr<UDirectionalLightComponent> Sun;
	UPROPERTY() TObjectPtr<USkyLightComponent> Sky;
	UPROPERTY() TObjectPtr<USkyAtmosphereComponent> Atmosphere;
	UPROPERTY() TObjectPtr<UExponentialHeightFogComponent> Fog;
	UPROPERTY() TObjectPtr<UVolumetricCloudComponent> Cloud;
	UPROPERTY() TObjectPtr<UPostProcessComponent> Post;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Dome;
	UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> DomeMat;
	/** HDRI'daki gunesin kubbe donusu sifirken bulundugu dunya yonu (derece); olcumle bulunur. */
	double SkyYawOffset = 306.3;

	EKTimeOfDay TimeOfDay = EKTimeOfDay::Dawn;
	int32 Quality = 1;
};
