#include "KapadokyaWorld.h"
#include "KapadokyaRider.h"
#include "KapadokyaTrack.h"
#include "Components/TextRenderComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/TextureCube.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/StaticMesh.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInterface.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	TSharedPtr<FJsonObject> LoadJson(const FString& Name)
	{
		FString Text;
		const FString Path = FPaths::ProjectContentDir() / TEXT("Kapadokya/Data") / Name;
		if (!FFileHelper::LoadFileToString(Text, *Path))
		{
			return nullptr;
		}
		TSharedPtr<FJsonObject> Root;
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
		FJsonSerializer::Deserialize(Reader, Root);
		return Root;
	}

	void SetCVar(const TCHAR* Name, int32 Value)
	{
		if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(Name))
		{
			Var->Set(Value, ECVF_SetByCode);
		}
	}

	void SetCVarF(const TCHAR* Name, float Value)
	{
		if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(Name))
		{
			Var->Set(Value, ECVF_SetByCode);
		}
	}
}

AKapadokyaWorld::AKapadokyaWorld()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent->SetMobility(EComponentMobility::Static);
	Sun = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Sun"));
	Sun->SetupAttachment(RootComponent);
	Sun->SetMobility(EComponentMobility::Movable);
	Sun->bAtmosphereSunLight = true;
	Sun->SetCastShadows(true);
	Sky = CreateDefaultSubobject<USkyLightComponent>(TEXT("Sky"));
	Sky->SetupAttachment(RootComponent);
	Sky->SetMobility(EComponentMobility::Movable);
	Sky->bRealTimeCapture = true;
	Sky->SetIntensity(1.6f);
	Atmosphere = CreateDefaultSubobject<USkyAtmosphereComponent>(TEXT("Atmosphere"));
	Atmosphere->SetupAttachment(RootComponent);
	Fog = CreateDefaultSubobject<UExponentialHeightFogComponent>(TEXT("Fog"));
	Fog->SetupAttachment(RootComponent);
	Cloud = CreateDefaultSubobject<UVolumetricCloudComponent>(TEXT("Cloud"));
	Cloud->SetupAttachment(RootComponent);
	Dome = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Dome"));
	Dome->SetupAttachment(RootComponent);
	Dome->SetCastShadow(false);
	Dome->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Dome->SetWorldScale3D(FVector(40000.0));
	Dome->bAffectDistanceFieldLighting = false;
	Dome->bVisibleInRayTracing = false;
	Post = CreateDefaultSubobject<UPostProcessComponent>(TEXT("Post"));
	Post->SetupAttachment(RootComponent);
	Post->bUnbound = true;
}

void AKapadokyaWorld::BeginPlay()
{
	Super::BeginPlay();
	if (UMaterialInterface* CloudMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst.m_SimpleVolumetricCloud_Inst")))
	{
		Cloud->SetMaterial(CloudMat);
	}
	Dome->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere")));
	if (UMaterialInterface* DomeBase = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Kapadokya/Mat/M_SkyDome.M_SkyDome")))
	{
		DomeMat = UMaterialInstanceDynamic::Create(DomeBase, this);
		Dome->SetMaterial(0, DomeMat);
	}
	BuildStatic();
	BuildPlacements();
	ApplyTimeOfDay(TimeOfDay);
}

void AKapadokyaWorld::BuildStatic()
{
	const auto AddMesh = [this](const FString& Path, bool bCollide)
	{
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Path);
		if (!Mesh)
		{
			UE_LOG(LogTemp, Error, TEXT("Mesh yok: %s"), *Path);
			return;
		}
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(Mesh);
		C->SetMobility(EComponentMobility::Static);
		C->SetCollisionEnabled(bCollide ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
		C->SetCollisionResponseToAllChannels(ECR_Block);
		C->SetupAttachment(RootComponent);
		C->RegisterComponent();
	};
	if (TSharedPtr<FJsonObject> Chunks = LoadJson(TEXT("chunks.json")))
	{
		for (const TSharedPtr<FJsonValue>& V : Chunks->GetArrayField(TEXT("terrain")))
		{
			const FString N = V->AsString();
			AddMesh(FString::Printf(TEXT("/Game/Kapadokya/Gen/Terrain/%s.%s"), *N, *N), true);
		}
	}
	AddMesh(TEXT("/Game/Kapadokya/Gen/Road.Road"), true);
	AddMesh(TEXT("/Game/Kapadokya/Gen/Horizon.Horizon"), false);
	AddMesh(TEXT("/Game/Kapadokya/Gen/Water.Water"), false);

	// Baslangic/bitis kemeri yazisi (her iki yuz)
	const FKapadokyaTrack& Track = FKapadokyaTrack::Get();
	if (Track.IsValid())
	{
		const double LineS = 36000.0;
		const FVector At = Track.PosAt(LineS);
		const FRotator Facing = Track.TangentAt(LineS).Rotation();
		for (int32 Side = 0; Side < 2; ++Side)
		{
			UTextRenderComponent* Label = NewObject<UTextRenderComponent>(this);
			Label->SetText(FText::FromString(TEXT("KAPADOKYA TURU")));
			Label->SetHorizontalAlignment(EHTA_Center);
			Label->SetVerticalAlignment(EVRTA_TextCenter);
			Label->SetWorldSize(82.f);
			Label->SetTextRenderColor(FColor(245, 235, 215));
			Label->SetMobility(EComponentMobility::Movable);
			Label->SetupAttachment(RootComponent);
			const double Offset = Side == 0 ? -10.0 : 10.0;
			const FVector Dir = Track.TangentAt(LineS);
			Label->SetWorldLocationAndRotation(At + Dir * Offset + FVector(0, 0, 565.0), FRotator(0.0, Facing.Yaw + (Side == 0 ? 180.0 : 0.0), 0.0));
			Label->RegisterComponent();
		}
	}
}

void AKapadokyaWorld::BuildPlacements()
{
	// Bicim: { "meshes": { "<varlik>": { "collide": bool, "cull": metre, "t": [x,y,z,yaw,scale, x,y,z,yaw,scale, ...] } } }
	TSharedPtr<FJsonObject> Root = LoadJson(TEXT("placements.json"));
	if (!Root)
	{
		return;
	}
	const TSharedPtr<FJsonObject>* Meshes;
	if (!Root->TryGetObjectField(TEXT("meshes"), Meshes))
	{
		return;
	}
	for (const auto& Pair : (*Meshes)->Values)
	{
		const FString Key(*Pair.Key);
		const FString Path = FString::Printf(TEXT("/Game/Kapadokya/Gen/%s.%s"), *Key, *FPaths::GetBaseFilename(Key));
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Path);
		if (!Mesh)
		{
			UE_LOG(LogTemp, Warning, TEXT("Yerlesim meshi yok: %s"), *Path);
			continue;
		}
		const TSharedPtr<FJsonObject> Obj = Pair.Value->AsObject();
		const TArray<TSharedPtr<FJsonValue>>& T = Obj->GetArrayField(TEXT("t"));
		UHierarchicalInstancedStaticMeshComponent* H = NewObject<UHierarchicalInstancedStaticMeshComponent>(this);
		H->SetStaticMesh(Mesh);
		H->SetMobility(EComponentMobility::Static);
		const bool bCollide = Obj->GetBoolField(TEXT("collide"));
		H->SetCollisionEnabled(bCollide ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
		H->SetCollisionResponseToAllChannels(ECR_Block);
		const float Cull = float(Obj->GetNumberField(TEXT("cull"))) * 100.f;
		H->SetCullDistances(int32(Cull * 0.85f), int32(Cull));
		H->SetupAttachment(RootComponent);
		TArray<FTransform> Instances;
		Instances.Reserve(T.Num() / 5);
		for (int32 I = 0; I + 4 < T.Num(); I += 5)
		{
			const double Scale = T[I + 4]->AsNumber();
			Instances.Add(FTransform(FRotator(0.0, T[I + 3]->AsNumber(), 0.0),
				FVector(T[I]->AsNumber(), T[I + 1]->AsNumber(), T[I + 2]->AsNumber()) * 100.0, FVector(Scale)));
		}
		// Seyirci: her kisiye farkli gomlek rengi (malzeme PerInstanceCustomData okur)
		const bool bCrowd = Key.StartsWith(TEXT("C_Crowd"));
		if (bCrowd)
		{
			H->NumCustomDataFloats = 3;
		}
		H->AddInstances(Instances, false);
		H->RegisterComponent();
		if (bCrowd)
		{
			static const FLinearColor Shirts[] = { {0.62f,0.05f,0.05f}, {0.08f,0.16f,0.42f}, {0.78f,0.76f,0.70f}, {0.10f,0.30f,0.22f}, {0.55f,0.40f,0.12f}, {0.25f,0.25f,0.28f}, {0.70f,0.30f,0.10f}, {0.40f,0.12f,0.30f} };
			FRandomStream ShirtRng(GetTypeHash(Key));
			for (int32 I = 0; I < Instances.Num(); ++I)
			{
				const FLinearColor& C = Shirts[ShirtRng.RandRange(0, UE_ARRAY_COUNT(Shirts) - 1)];
				H->SetCustomDataValue(I, 0, C.R, false);
				H->SetCustomDataValue(I, 1, C.G, false);
				H->SetCustomDataValue(I, 2, C.B, false);
			}
			H->MarkRenderStateDirty();
		}
		if (Key.StartsWith(TEXT("Cali")) || Key == TEXT("Bayrak") || Key == TEXT("Flama"))
		{
			SmallCasters.Add(H);
			H->SetCastShadow(Quality >= 2);
		}
	}
}

void AKapadokyaWorld::ApplyTimeOfDay(EKTimeOfDay Time)
{
	TimeOfDay = Time;
	struct FPreset { float Pitch, Yaw, Lux, Temp, Fog, FogHeight; FLinearColor FogTint; float Exposure; };
	static const FPreset Presets[] = {
		// Gundogumu: alcak sicak gunes, vadide sis
		{ -19.9f, 118.f, 10.f, 4800.f, 0.012f, 0.10f, FLinearColor(0.85f, 0.62f, 0.50f), 1.2f },
		{ -47.8f, 200.f, 11.f, 5800.f, 0.004f, 0.25f, FLinearColor(0.6f, 0.72f, 0.9f), -0.6f },
		{ -9.f, 288.f, 10.f, 4100.f, 0.012f, 0.14f, FLinearColor(0.95f, 0.55f, 0.35f), 1.1f },
	};
	const FPreset& P = Presets[int32(Time)];
	Sun->SetWorldRotation(FRotator(P.Pitch, P.Yaw, 0.f));
	Sun->SetIntensity(P.Lux);
	Sun->bUseTemperature = true;
	Sun->SetTemperature(P.Temp);
	Sun->SetDynamicShadowDistanceMovableLight(25000.f);
	Fog->SetFogDensity(P.Fog);
	Fog->SetFogHeightFalloff(P.FogHeight);
	Fog->SetFogInscatteringColor(P.FogTint * 0.4f);
	Fog->SetVolumetricFog(Quality >= 2);
	Fog->SetWorldLocation(FVector(0.f, 0.f, -4500.f));
	FPostProcessSettings& S = Post->Settings;
	S.bOverride_AutoExposureMethod = true;
	S.AutoExposureMethod = AEM_Manual;
	S.bOverride_AutoExposureBias = true;
	S.AutoExposureBias = P.Exposure;
	S.bOverride_AutoExposureApplyPhysicalCameraExposure = true;
	S.AutoExposureApplyPhysicalCameraExposure = false;
	S.bOverride_BloomIntensity = true;
	S.BloomIntensity = 0.45f;
	S.bOverride_VignetteIntensity = true;
	S.VignetteIntensity = 0.28f;
	S.bOverride_FilmSlope = true;
	S.FilmSlope = 0.86f;
	S.bOverride_FilmToe = true;
	S.FilmToe = 0.54f;
	S.bOverride_ColorSaturation = true;
	S.ColorSaturation = FVector4(1.04, 1.03, 1.0, 1.0);
	S.bOverride_DepthOfFieldFstop = false;
	ApplySky(P.Yaw);
	Post->MarkRenderStateDirty();
}

void AKapadokyaWorld::ApplySky(float SunYaw)
{
	// Dusuk/Orta: fotograf HDRI kubbe (yaklasik 5 ms bulut + gercek zamanli yakalama kazanci). Yuksek: hacimsel bulut.
	const bool bDome = Quality < 2 && DomeMat;
	Dome->SetVisibility(bDome);
	Cloud->SetVisibility(!bDome);
	SetCVar(TEXT("r.VolumetricCloud"), bDome ? 0 : 1);
	if (bDome)
	{
		static const TCHAR* Names[] = { TEXT("morning"), TEXT("noon"), TEXT("sunset") };
		const FString N = FString::Printf(TEXT("/Game/Kapadokya/Sky/T_sky_%s.T_sky_%s"), Names[int32(TimeOfDay)], Names[int32(TimeOfDay)]);
		UTextureCube* Cube = LoadObject<UTextureCube>(nullptr, *N);
		double DomeYaw = SkyYawOffset;
		FParse::Value(FCommandLine::Get(), TEXT("-KDomeYaw="), DomeYaw);
		// Kubbedeki gunes, isik yonunun tersine gelsin
		const float Yaw = float(FRotator::NormalizeAxis(float(DomeYaw) - SunYaw - 180.f));
		DomeMat->SetTextureParameterValue(TEXT("Cube"), Cube);
		DomeMat->SetScalarParameterValue(TEXT("Yaw"), Yaw);
		// Gun batimi HDRI'si cok daha parlak: pozu bozmasin
		const float SkyScale = TimeOfDay == EKTimeOfDay(2) ? 0.4f : 1.f;
		DomeMat->SetScalarParameterValue(TEXT("Intensity"), SkyScale);
		Sky->bRealTimeCapture = false;
		Sky->SourceType = SLS_SpecifiedCubemap;
		Sky->SourceCubemapAngle = FMath::Fmod(Yaw + 360.f, 360.f);
		Sky->SetCubemap(Cube);
		// Lumen sekmesi yok: golgeli yuzler kapkara kalmasin
		Sky->SetIntensity(1.5f * SkyScale);
	}
	else
	{
		Sky->SourceType = SLS_CapturedScene;
		Sky->bRealTimeCapture = true;
		Sky->SetIntensity(1.6f);
	}
	Sky->MarkRenderStateDirty();
	Sky->RecaptureSky();
}

void AKapadokyaWorld::ApplyQuality(int32 Level)
{
	Quality = FMath::Clamp(Level, 0, 3);
	SetCVar(TEXT("sg.ViewDistanceQuality"), Quality);
	SetCVar(TEXT("sg.ShadowQuality"), FMath::Min(Quality + 1, 3));
	SetCVar(TEXT("sg.GlobalIlluminationQuality"), FMath::Max(Quality, 1));
	SetCVar(TEXT("sg.ReflectionQuality"), FMath::Max(Quality, 1));
	SetCVar(TEXT("sg.PostProcessQuality"), FMath::Min(Quality + 1, 3));
	SetCVar(TEXT("sg.EffectsQuality"), Quality);
	SetCVar(TEXT("sg.FoliageQuality"), Quality);
	SetCVar(TEXT("sg.ShadingQuality"), FMath::Min(Quality + 1, 3));
	SetCVar(TEXT("sg.TextureQuality"), FMath::Min(Quality + 1, 3));
	const float ScreenPct[] = { 67.f, 80.f, 80.f, 100.f };
	SetCVarF(TEXT("r.ScreenPercentage"), ScreenPct[Quality]);
	// Fansiz kasa isinip GPU yavaslayinca FPS yerine cozunurluk dussun
	SetCVar(TEXT("r.DynamicRes.OperationMode"), Quality < 2 ? 2 : 0);
	SetCVarF(TEXT("r.DynamicRes.MinScreenPercentage"), 45.f);
	SetCVarF(TEXT("r.DynamicRes.MaxScreenPercentage"), ScreenPct[Quality]);
	SetCVarF(TEXT("r.DynamicRes.FrameTimeBudget"), Quality == 0 ? 16.6f : 25.f);
	// Isiyi bastan azalt: GPU kare butcesinin %25'ini bos birakir
	SetCVarF(TEXT("r.DynamicRes.TargetedGPUHeadRoomPercentage"), 25.f);
	// Olcum (M2, 1600x900): TSR->TAA 16 ms, bulut 9 ms kazandirir. Alt kademeler bunlari kullanir.
	SetCVar(TEXT("r.AntiAliasingMethod"), Quality >= 2 ? 4 : 2);
	const float CloudSamples[] = { 0.35f, 0.5f, 1.f, 1.f };
	Cloud->SetViewSampleCountScale(CloudSamples[Quality]);
	Cloud->SetShadowViewSampleCountScale(CloudSamples[Quality]);
	// Olcum (M2, 1600x900, 67%): Lumen 13.6 ms, bulut 5 ms, gunes golgesi 4 ms. Acik havada Lumen'in gorsel farki kucuk.
	SetCVar(TEXT("r.DynamicGlobalIlluminationMethod"), Quality >= 2 ? 1 : 0);
	SetCVar(TEXT("r.ReflectionMethod"), Quality >= 2 ? 1 : 0);
	SetCVar(TEXT("r.Shadow.Virtual.ResolutionLodBiasDirectional"), Quality == 0 ? 1 : 0);
	const int32 Blur[] = { 0, 2, 4, 4 };
	SetCVar(TEXT("r.MotionBlurQuality"), Blur[Quality]);
	SetCVarF(TEXT("r.Tonemapper.Sharpen"), Quality < 2 ? 0.8f : 0.f);
	SetCVarF(TEXT("r.Nanite.MaxPixelsPerEdge"), Quality == 0 ? 2.f : 1.f);
	SetCVar(TEXT("r.Shadow.Virtual.NonNanite.IncludeInCoarsePages"), Quality >= 2 ? 1 : 0);
	const double ShadowNear[] = { 9.0, 20.0, 1000.0, 1000.0 };
	AKapadokyaRider::ShadowNearM = ShadowNear[Quality];
	for (UHierarchicalInstancedStaticMeshComponent* H : SmallCasters)
	{
		H->SetCastShadow(Quality >= 2);
	}
	if (Fog)
	{
		Fog->SetVolumetricFog(Quality >= 2);
	}
	if (Sun)
	{
		ApplySky(Sun->GetComponentRotation().Yaw);
	}
}
