#include "KapadokyaRider.h"
#include "KapadokyaTrack.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Components/InputComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "PhysicsEngine/BodyInstance.h"
#include "PhysicsEngine/BodySetup.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "ReferenceSkeleton.h"
#include "Sound/SoundBase.h"

namespace
{
	// bl_bike.py ile ayni (cm)
	const FVector HeadPivot(43.0, 0.0, 71.5);
	const FVector HeadTop(38.5, 0.0, 86.5);
	const FVector FrontAxle(58.5, 0.0, 34.0);
	const FVector RearAxle(-40.5, 0.0, 34.0);
	const FVector BB(0.0, 0.0, 26.8);
	const double CrankLen = 17.25;
	const double PedalY = 11.0;
	const FVector Hood(56.6, 20.0, 90.6);       // gidon uzerinde el
	const FVector Drop(57.0, 20.5, 78.0);       // alt tutus
	const FVector SaddleSeat(-21.0, 0.0, 104.0);

	UStaticMesh* LoadMesh(const TCHAR* Name)
	{
		return LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("/Game/Kapadokya/Gen/%s.%s"), Name, Name));
	}

	FORCEINLINE FVector BikeToMesh(const FVector& B) { return FVector(-B.Y, B.X, B.Z); }

	/** Iki kemikli IK: Root, Joint ve End pozisyonlarini verir. */
	void SolveTwoBone(const FVector& A, const FVector& Target, double L1, double L2, const FVector& Pole, FVector& OutJoint, FVector& OutEnd)
	{
		FVector D = Target - A;
		double Len = D.Size();
		const double MaxLen = (L1 + L2) * 0.999;
		if (Len > MaxLen)
		{
			D *= MaxLen / Len;
			Len = MaxLen;
		}
		const FVector Dir = D.GetSafeNormal();
		const double CosA = FMath::Clamp((L1 * L1 + Len * Len - L2 * L2) / (2.0 * L1 * Len), -1.0, 1.0);
		const double SinA = FMath::Sqrt(1.0 - CosA * CosA);
		FVector PoleDir = (Pole - Dir * FVector::DotProduct(Pole, Dir)).GetSafeNormal();
		OutJoint = A + Dir * (L1 * CosA) + PoleDir * (L1 * SinA);
		OutEnd = A + D;
	}

	FQuat AimBone(const FTransform& RefParent, const FTransform& RefChild, const FVector& NewParent, const FVector& NewChild)
	{
		const FVector RefDir = (RefChild.GetLocation() - RefParent.GetLocation()).GetSafeNormal();
		const FVector NewDir = (NewChild - NewParent).GetSafeNormal();
		return FQuat::FindBetweenNormals(RefDir, NewDir) * RefParent.GetRotation();
	}

	USoundBase* LoadSound(const TCHAR* Name)
	{
		return LoadObject<USoundBase>(nullptr, *FString::Printf(TEXT("/Game/Kapadokya/Audio/%s.%s"), Name, Name));
	}
}

AKapadokyaRider::AKapadokyaRider()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	LeanRoot = CreateDefaultSubobject<USceneComponent>(TEXT("LeanRoot"));
	LeanRoot->SetupAttachment(Root);

	const auto MakeMesh = [this](const TCHAR* Name, USceneComponent* AttachTo)
	{
		UStaticMeshComponent* C = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		C->SetupAttachment(AttachTo);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetMobility(EComponentMobility::Movable);
		return C;
	};
	FrameMesh = MakeMesh(TEXT("Frame"), LeanRoot);
	SteerPivot = CreateDefaultSubobject<USceneComponent>(TEXT("SteerPivot"));
	SteerPivot->SetupAttachment(LeanRoot);
	SteerPivot->SetRelativeLocation(HeadPivot);
	SteerMesh = MakeMesh(TEXT("Steer"), SteerPivot);
	FrontWheel = MakeMesh(TEXT("FrontWheel"), SteerPivot);
	FrontWheel->SetRelativeLocation(FrontAxle - HeadPivot);
	RearWheel = MakeMesh(TEXT("RearWheel"), LeanRoot);
	RearWheel->SetRelativeLocation(RearAxle);
	CrankMesh = MakeMesh(TEXT("Crank"), LeanRoot);
	CrankMesh->SetRelativeLocation(BB);
	PedalR = MakeMesh(TEXT("PedalR"), LeanRoot);
	PedalL = MakeMesh(TEXT("PedalL"), LeanRoot);

	Body = CreateDefaultSubobject<UPoseableMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(LeanRoot);
	Body->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Face = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Face"));
	Face->SetupAttachment(Body);
	Face->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Outfit = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Outfit"));
	Outfit->SetupAttachment(Body);
	Outfit->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Helmet = MakeMesh(TEXT("Helmet"), Body);
	Glasses = MakeMesh(TEXT("Glasses"), Body);

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Root);
	Camera->SetUsingAbsoluteLocation(true);
	Camera->SetUsingAbsoluteRotation(true);
	Camera->PostProcessBlendWeight = 0.f;

	AutoPossessPlayer = EAutoReceiveInput::Disabled;
}

void AKapadokyaRider::InitRider(int32 InId, const FString& InName, const FString& InTeam, const FLinearColor& TeamColor, const FLinearColor& TeamColor2, bool bInPlayer, double StartS, double StartLat, double Strength)
{
	Id = InId;
	RiderName = InName;
	TeamName = InTeam;
	Color = TeamColor;
	bIsPlayer = bInPlayer;
	AIStrength = Strength;
	AISeed = InId * 17.31;
	AILane = StartLat;
	Bike.Params.CP = 310.0 * (bInPlayer ? 1.0 : Strength);
	Bike.State.WPrime = Bike.Params.WPrimeMax;

	BuildVisual();

	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	TrackS = T.Wrap(StartS);
	TotalS = StartS;
	Lateral = StartLat;
	AssistLane = StartLat;
	const FVector Base = T.PosAt(TrackS) + T.RightAt(TrackS) * StartLat;
	Pos = Base;
	GroundZ = Base.Z;
	const FVector Tan = T.TangentAt(TrackS);
	Bike.State.Heading = FMath::Atan2(Tan.Y, Tan.X);
	SetActorLocation(Pos);

	if (PaintMID)
	{
		PaintMID->SetVectorParameterValue(TEXT("Color"), TeamColor);
	}
	JerseyA = TeamColor;
	JerseyB = TeamColor2;
	ApplyTeamToJersey();
	if (BodyMID)
	{
		BodyMID->SetVectorParameterValue(TEXT("Jersey"), TeamColor);
		BodyMID->SetVectorParameterValue(TEXT("Jersey2"), TeamColor2);
		// Rider tenini hafif cesitlendir
		const double Skin = 0.85 + 0.25 * FMath::Frac(AISeed * 0.37);
		BodyMID->SetVectorParameterValue(TEXT("Skin"), FLinearColor(0.60f * Skin, 0.40f * Skin, 0.30f * Skin));
	}
	if (bIsPlayer)
	{
		SndTyre = UGameplayStatics::SpawnSoundAttached(LoadSound(TEXT("S_Tyre")), Root);
		SndWind = UGameplayStatics::SpawnSoundAttached(LoadSound(TEXT("S_Wind")), Root);
		SndFreewheel = UGameplayStatics::SpawnSoundAttached(LoadSound(TEXT("S_Freewheel")), Root);
		SndChain = UGameplayStatics::SpawnSoundAttached(LoadSound(TEXT("S_Chain")), Root);
		SndCobble = UGameplayStatics::SpawnSoundAttached(LoadSound(TEXT("S_Cobble")), Root);
		SndBreath = UGameplayStatics::SpawnSoundAttached(LoadSound(TEXT("S_Breath")), Root);
		SndShift = LoadSound(TEXT("S_Shift"));
		SndCrash = LoadSound(TEXT("S_Crash"));
	}
}

void AKapadokyaRider::BuildVisual()
{
	UStaticMesh* Frame = LoadMesh(TEXT("BikeFrame"));
	UStaticMesh* Steer = LoadMesh(TEXT("BikeSteer"));
	UStaticMesh* Wheel = LoadMesh(TEXT("BikeWheel"));
	UStaticMesh* Crank = LoadMesh(TEXT("BikeCrank"));
	UStaticMesh* Pedal = LoadMesh(TEXT("BikePedal"));
	FrameMesh->SetStaticMesh(Frame);
	SteerMesh->SetStaticMesh(Steer);
	FrontWheel->SetStaticMesh(Wheel);
	RearWheel->SetStaticMesh(Wheel);
	CrankMesh->SetStaticMesh(Crank);
	PedalR->SetStaticMesh(Pedal);
	PedalL->SetStaticMesh(Pedal);
	if (Frame && Frame->GetStaticMaterials().Num() > 0)
	{
		PaintMID = UMaterialInstanceDynamic::Create(Frame->GetMaterial(0), this);
		FrameMesh->SetMaterial(0, PaintMID);
		SteerMesh->SetMaterial(0, PaintMID);
	}

	// Gercek insan: MetaHuman govde ve yuz. Yoksa (Tools/mh_gui.sh calismadiysa) mankene duser.
	// Her sporcu dort kisiden biri; yeni kimlik uretilmediyse Lorenzo'ya duser
	static const TCHAR* People[] = { TEXT("Lorenzo"), TEXT("Mateo"), TEXT("Jorge"), TEXT("Dominic") };
	const FString Person = People[FMath::Abs(GetUniqueID()) % 4];
	const auto HumanPath = [](const FString& Who, const TCHAR* Part, const TCHAR* Suffix)
	{
		return FString::Printf(TEXT("/Game/Kapadokya/MH/Built/%s/MH_%s/%s/%sMH_%s%s.%sMH_%s%s"), *Who, *Who, Part, Part[0] == TEXT('C') ? TEXT("") : TEXT("SKM_"), *Who, Suffix, Part[0] == TEXT('C') ? TEXT("") : TEXT("SKM_"), *Who, Suffix);
	};
	FString Who = Person;
	USkeletalMesh* Human = LoadObject<USkeletalMesh>(nullptr, *HumanPath(Who, TEXT("Body"), TEXT("_BodyMesh")));
	if (!Human)
	{
		Who = TEXT("Lorenzo");
		Human = LoadObject<USkeletalMesh>(nullptr, *HumanPath(Who, TEXT("Body"), TEXT("_BodyMesh")));
	}
	USkeletalMesh* HumanFace = LoadObject<USkeletalMesh>(nullptr, *HumanPath(Who, TEXT("Face"), TEXT("_FaceMesh")));
	USkeletalMesh* Manny = Human ? Human : LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
	if (Manny)
	{
		Body->SetSkinnedAssetAndUpdate(Manny);
		if (Human && HumanFace)
		{
			Face->SetSkeletalMeshAsset(HumanFace);
			Face->SetLeaderPoseComponent(Body);
			if (USkeletalMesh* Clothes = LoadObject<USkeletalMesh>(nullptr, *HumanPath(Who, TEXT("Clothing"), TEXT("_Outfits"))))
			{
				Outfit->SetSkeletalMeshAsset(Clothes);
				Outfit->SetLeaderPoseComponent(Body);
				if (UMaterialInterface* Cloth = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Kapadokya/Mat/M_JerseyCloth.M_JerseyCloth")))
				{
					// Tek numarali yuvalar gomlek, cift numaralilar sort
					JerseyMID = UMaterialInstanceDynamic::Create(Cloth, this);
					UMaterialInstanceDynamic* ShortMID = UMaterialInstanceDynamic::Create(Cloth, this);
					ShortMID->SetVectorParameterValue(TEXT("Jersey"), FLinearColor(0.012f, 0.012f, 0.016f));
					ShortMID->SetVectorParameterValue(TEXT("Jersey2"), FLinearColor(0.012f, 0.012f, 0.016f));
					for (int32 I = 0; I < Outfit->GetNumMaterials(); ++I)
					{
						Outfit->SetMaterial(I, (I % 2) ? JerseyMID.Get() : ShortMID);
					}
					ApplyTeamToJersey();
				}
			}
		}
		UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, Human ? TEXT("/Game/Kapadokya/Mat/M_RiderMH.M_RiderMH") : TEXT("/Game/Kapadokya/Mat/M_Rider.M_Rider"));
		if (Base)
		{
			BodyMID = UMaterialInstanceDynamic::Create(Base, this);
			if (Human)
			{
				// Kimligin kendi cildi
				const FString Baked = FString::Printf(TEXT("/Game/Kapadokya/MH/Built/%s/MH_%s/Body/Baked/"), *Who, *Who);
				for (const TCHAR* Tex : { TEXT("BC"), TEXT("N"), TEXT("SRMF") })
				{
					const FString TexName = FString::Printf(TEXT("T_Body_%s_VT"), Tex);
					if (UTexture* Loaded = LoadObject<UTexture>(nullptr, *(Baked + TexName + TEXT(".") + TexName)))
					{
						BodyMID->SetTextureParameterValue(FName(Tex), Loaded);
					}
				}
			}
			for (int32 I = 0; I < Body->GetNumMaterials(); ++I)
			{
				Body->SetMaterial(I, BodyMID);
			}
		}
		InitPose();
	}
	if (UStaticMesh* H = LoadMesh(TEXT("Helmet")))
	{
		Helmet->SetStaticMesh(H);
	}
	if (UStaticMesh* G = LoadMesh(TEXT("Glasses")))
	{
		Glasses->SetStaticMesh(G);
	}
	if (!bIsPlayer)
	{
		// Rakipler kendi golgesini sadeletir
		FrontWheel->SetForcedLodModel(0);
	}
}

void AKapadokyaRider::InitPose()
{
	USkeletalMesh* Mesh = Cast<USkeletalMesh>(Body->GetSkinnedAsset());
	if (!Mesh)
	{
		return;
	}
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	const int32 Num = Ref.GetNum();
	RefLocal.SetNum(Num);
	RefCS.SetNum(Num);
	Parent.SetNum(Num);
	PoseCS.SetNum(Num);
	const TArray<FTransform>& Pose = Ref.GetRefBonePose();
	for (int32 I = 0; I < Num; ++I)
	{
		RefLocal[I] = Pose[I];
		Parent[I] = Ref.GetParentIndex(I);
		RefCS[I] = Parent[I] >= 0 ? Pose[I] * RefCS[Parent[I]] : Pose[I];
		const FString N = Ref.GetBoneName(I).ToString();
		if (N.StartsWith(TEXT("index_")) || N.StartsWith(TEXT("middle_")) || N.StartsWith(TEXT("ring_")) || N.StartsWith(TEXT("pinky_")))
		{
			FingerBones.Add(I);
		}
	}
	const auto Find = [&Ref](const TCHAR* Name) { return Ref.FindBoneIndex(FName(Name)); };
	Bones.Pelvis = Find(TEXT("pelvis"));
	Bones.Spine[0] = Find(TEXT("spine_01"));
	Bones.Spine[1] = Find(TEXT("spine_02"));
	Bones.Spine[2] = Find(TEXT("spine_03"));
	Bones.Spine[3] = Find(TEXT("spine_04"));
	Bones.Spine[4] = Find(TEXT("spine_05"));
	Bones.Neck = Find(TEXT("neck_01"));
	Bones.Head = Find(TEXT("head"));
	Bones.ClavicleL = Find(TEXT("clavicle_l"));
	Bones.UpperArmL = Find(TEXT("upperarm_l"));
	Bones.LowerArmL = Find(TEXT("lowerarm_l"));
	Bones.HandL = Find(TEXT("hand_l"));
	Bones.ClavicleR = Find(TEXT("clavicle_r"));
	Bones.UpperArmR = Find(TEXT("upperarm_r"));
	Bones.LowerArmR = Find(TEXT("lowerarm_r"));
	Bones.HandR = Find(TEXT("hand_r"));
	Bones.ThighL = Find(TEXT("thigh_l"));
	Bones.CalfL = Find(TEXT("calf_l"));
	Bones.FootL = Find(TEXT("foot_l"));
	Bones.BallL = Find(TEXT("ball_l"));
	Bones.ThighR = Find(TEXT("thigh_r"));
	Bones.CalfR = Find(TEXT("calf_r"));
	Bones.FootR = Find(TEXT("foot_r"));
	Bones.BallR = Find(TEXT("ball_r"));
	bPoseReady = Bones.Pelvis >= 0 && Bones.Spine[4] >= 0 && Bones.Head >= 0 && Bones.HandR >= 0 && Bones.FootR >= 0 && Bones.FootL >= 0;
	if (bPoseReady)
	{
		// Bisiklet saginin Y+ oldugu gore sag kemigin mesh X isareti
		RightSideSign = RefCS[Bones.ThighR].GetLocation().X >= 0.0 ? 1.0 : -1.0;
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Manny iskeleti beklenen kemikleri icermiyor"));
	}
}

void AKapadokyaRider::UpdatePose(float Dt)
{
	if (bIsPlayer && FParse::Param(FCommandLine::Get(), TEXT("KBoneLog")))
	{
		static bool bLogged = false;
		if (!bLogged && bPoseReady)
		{
			bLogged = true;
			for (const int32 B : { Bones.Pelvis, Bones.Neck, Bones.Head, Bones.UpperArmL, Bones.LowerArmL, Bones.HandL, Bones.ThighL, Bones.CalfL, Bones.FootL, Bones.BallL })
			{
				if (RefCS.IsValidIndex(B))
				{
					UE_LOG(LogTemp, Display, TEXT("KBONE %s %s"), *Body->GetBoneName(B).ToString(), *RefCS[B].GetLocation().ToString());
				}
			}
		}
	}
	if (!bPoseReady || bRespawning || Body->BoneSpaceTransforms.Num() != RefLocal.Num())
	{
		return;
	}
	// Uzak rakiplerde pozu her karede hesaplama
	if (!bIsPlayer)
	{
		if (const APlayerController* PC = GetWorld()->GetFirstPlayerController())
		{
			if (const APawn* P = PC->GetPawn())
			{
				const double Dist = FVector::Dist(P->GetActorLocation(), GetActorLocation());
				const int32 Skip = Dist > 12000.0 ? 6 : (Dist > 4000.0 ? 2 : 0);
				if (PoseFrameSkip++ < Skip)
				{
					return;
				}
				PoseFrameSkip = 0;
			}
		}
	}
	const FBikeState& S = Bike.State;

	// Durus: oturma, ayakta tirmanis/sprint, aero
	const bool bStand = !bRespawning && (bInSprint || (!bIsPlayer && S.Power > Bike.Params.CP * 1.25) || (GradeNow > 0.075 && S.Power > Bike.Params.CP * 0.85));
	StandAlpha = FMath::FInterpTo(StandAlpha, bStand && S.Speed > 2.0 ? 1.0 : 0.0, double(Dt), 3.5);
	AeroAlpha = FMath::FInterpTo(AeroAlpha, bInTuck ? 1.0 : (S.Speed > 14.0 && S.Power < 150.0 ? 0.65 : 0.0), double(Dt), 2.8);
	const double Rock = FMath::Sin(S.CrankAngle) * (0.35 + 0.65 * StandAlpha);
	// Ayakta sallanirken bisiklet alttan yana yatar (kullanici fark etmesi icin)
	const double BodyRoll = Rock * 5.0;

	const FVector PelvisB = SaddleSeat + FVector(2.0 + 14.0 * StandAlpha + 2.0 * AeroAlpha, Rock * 1.4, 6.0 * StandAlpha - 2.0 * AeroAlpha);
	const FVector PelvisM = BikeToMesh(PelvisB);

	PoseCS[Bones.Pelvis] = RefCS[Bones.Pelvis];

	// Govde egimi: oturusta ileri, damla tutusta daha ileri
	const double TorsoTotal = FMath::Lerp(58.0, 68.0, AeroAlpha) - 14.0 * StandAlpha;
	const double PelvisTilt = FMath::Lerp(TorsoTotal * 0.42, TorsoTotal * 0.28, StandAlpha);
	const FVector Lat(1.0, 0.0, 0.0);
	const FQuat PelvisQ = FQuat(FVector(0, 1, 0), FMath::DegreesToRadians(BodyRoll * RightSideSign * -0.5)) * FQuat(Lat, FMath::DegreesToRadians(-PelvisTilt));
	PoseCS[Bones.Pelvis].SetLocation(PelvisM);
	PoseCS[Bones.Pelvis].SetRotation(PelvisQ * RefCS[Bones.Pelvis].GetRotation());

	// Tum iskelet: once ebeveyn duzeninde
	const int32 Num = RefLocal.Num();
	TArray<FTransform, TInlineAllocator<128>> Local;
	Local.SetNumUninitialized(Num);
	double SpineAngle = PelvisTilt;
	const double PerSpine = (TorsoTotal - PelvisTilt) / 5.0;
	TArray<double, TInlineAllocator<128>> Extra;
	Extra.Init(0.0, Num);
	for (int32 I = 0; I < 5; ++I)
	{
		SpineAngle += PerSpine;
		Extra[Bones.Spine[I]] = SpineAngle;
	}
	// FK: pelvis ve omurga
	FQuat NeckQ = FQuat::Identity;
	for (int32 I = 0; I < Num; ++I)
	{
		if (I == Bones.Pelvis)
		{
			continue;
		}
		const int32 P = Parent[I];
		if (P < 0)
		{
			PoseCS[I] = RefCS[I];
			continue;
		}
		PoseCS[I] = RefLocal[I] * PoseCS[P];
		if (Extra[I] != 0.0)
		{
			const FQuat Q = FQuat(Lat, FMath::DegreesToRadians(-Extra[I]));
			PoseCS[I].SetRotation(Q * RefCS[I].GetRotation());
		}
		else if (I == Bones.Neck)
		{
			// Bas yukari kalkar, yola bakar
			const FQuat Q = FQuat(Lat, FMath::DegreesToRadians(-(TorsoTotal - 38.0)));
			PoseCS[I].SetRotation(Q * RefCS[I].GetRotation());
		}
		else if (I == Bones.Head)
		{
			const double SteerLook = S.Lean * 22.0;
			const FQuat Q = FQuat(FVector(0, 0, 1), FMath::DegreesToRadians(SteerLook * -1.0)) * FQuat(Lat, FMath::DegreesToRadians(-(TorsoTotal - 50.0)));
			PoseCS[I].SetRotation(Q * RefCS[I].GetRotation());
		}
	}

	// Bacaklar: pedal hedefleri
	const double Angle = S.CrankAngle;
	const auto LegIK = [&](int32 Thigh, int32 Calf, int32 Foot, int32 Ball, double SideSign, double Phase)
	{
		// SideSign: bisiklet yani (+ sag). Kol 0 acida ileri bakar.
		const double A = Angle + Phase;
		const FVector PedalB = BB + FVector(FMath::Cos(A) * CrankLen, SideSign * PedalY, -FMath::Sin(A) * CrankLen);
		// Ayak bilegi: pedal ustunde, biraz arkada; pedal alt noktada topuk yukari
		const double Ankling = 0.55 * FMath::Sin(A + 0.8);
		const FVector Ankle = BikeToMesh(PedalB + FVector(-8.0, 0.0, 9.5));
		const FVector HipP = PoseCS[Thigh].GetLocation();
		const double L1 = (RefCS[Calf].GetLocation() - RefCS[Thigh].GetLocation()).Size();
		const double L2 = (RefCS[Foot].GetLocation() - RefCS[Calf].GetLocation()).Size();
		FVector Knee, End;
		// Diz one ve hafif disa
		SolveTwoBone(HipP, Ankle, L1, L2, BikeToMesh(FVector(1.0, SideSign * 0.08, 0.15)), Knee, End);
		PoseCS[Thigh].SetRotation(AimBone(RefCS[Thigh], RefCS[Calf], HipP, Knee));
		PoseCS[Calf].SetLocation(Knee);
		PoseCS[Calf].SetRotation(AimBone(RefCS[Calf], RefCS[Foot], Knee, End));
		PoseCS[Foot].SetLocation(End);
		const FQuat FootTilt = FQuat(Lat, Ankling * -0.45 - 0.15);
		PoseCS[Foot].SetRotation(FootTilt * RefCS[Foot].GetRotation());
		if (Ball >= 0)
		{
			PoseCS[Ball] = RefLocal[Ball] * PoseCS[Foot];
		}
	};
	const double RightSide = 1.0;
	LegIK(Bones.ThighR, Bones.CalfR, Bones.FootR, Bones.BallR, RightSide, 0.0);
	LegIK(Bones.ThighL, Bones.CalfL, Bones.FootL, Bones.BallL, -RightSide, UE_DOUBLE_PI);

	// Kollar: gidon hedefleri (gidon donusuyle birlikte)
	const FVector SteerAxis = (HeadTop - HeadPivot).GetSafeNormal();
	const FQuat SteerQ(SteerAxis, S.Steer);
	const auto ArmIK = [&](int32 Upper, int32 Lower, int32 Hand, double SideSign)
	{
		const FVector GripBase = FMath::Lerp(Hood, Drop, AeroAlpha);
		const FVector Grip = FVector(GripBase.X, GripBase.Y * SideSign, GripBase.Z);
		const FVector WorldGrip = HeadPivot + SteerQ.RotateVector(Grip - HeadPivot);
		// Bilek, kavrama noktasinin arkasinda ve az ustunde: avuc gidonun uzerine oturur
		const FVector Target = BikeToMesh(WorldGrip + FVector(-7.5, 0.0, 3.5));
		const FVector Shoulder = PoseCS[Upper].GetLocation();
		const double L1 = (RefCS[Lower].GetLocation() - RefCS[Upper].GetLocation()).Size();
		const double L2 = (RefCS[Hand].GetLocation() - RefCS[Lower].GetLocation()).Size();
		FVector Elbow, End;
		SolveTwoBone(Shoulder, Target, L1, L2, BikeToMesh(FVector(-0.3, SideSign * 0.9, -0.5)), Elbow, End);
		PoseCS[Upper].SetRotation(AimBone(RefCS[Upper], RefCS[Lower], Shoulder, Elbow));
		PoseCS[Lower].SetLocation(Elbow);
		PoseCS[Lower].SetRotation(AimBone(RefCS[Lower], RefCS[Hand], Elbow, End));
		PoseCS[Hand].SetLocation(End);
		// Avuc gidona dogru: on kol yonunde, biraz asagi
		const FVector ForeDir = (End - Elbow).GetSafeNormal();
		const FVector RefFore = (RefCS[Hand].GetLocation() - RefCS[Lower].GetLocation()).GetSafeNormal();
		PoseCS[Hand].SetRotation(FQuat::FindBetweenNormals(RefFore, ForeDir) * RefCS[Hand].GetRotation());
	};
	ArmIK(Bones.UpperArmR, Bones.LowerArmR, Bones.HandR, RightSide);
	ArmIK(Bones.UpperArmL, Bones.LowerArmL, Bones.HandL, -RightSide);

	// Parmaklar ve el/ayak alt kemikleri ebeveyn uzerinden
	for (int32 I = 0; I < Num; ++I)
	{
		const int32 P = Parent[I];
		if (P < 0)
		{
			continue;
		}
		const bool bFixed = I == Bones.Pelvis || I == Bones.ThighL || I == Bones.ThighR || I == Bones.CalfL || I == Bones.CalfR
			|| I == Bones.FootL || I == Bones.FootR || I == Bones.BallL || I == Bones.BallR
			|| I == Bones.UpperArmL || I == Bones.UpperArmR || I == Bones.LowerArmL || I == Bones.LowerArmR || I == Bones.HandL || I == Bones.HandR
			|| I == Bones.Spine[0] || I == Bones.Spine[1] || I == Bones.Spine[2] || I == Bones.Spine[3] || I == Bones.Spine[4]
			|| I == Bones.Neck || I == Bones.Head || I == Bones.ClavicleL || I == Bones.ClavicleR;
		if (!bFixed)
		{
			FTransform L = RefLocal[I];
			if (FingerBones.Contains(I))
			{
				L.SetRotation(FQuat(FVector(0, 0, 1), FMath::DegreesToRadians(-64.0)) * L.GetRotation());
			}
			PoseCS[I] = L * PoseCS[P];
		}
	}

	// Kask ve gozluk: bas kemiginin referanstan donusu kadar doner (model +X, mesh icinde +Y one bakar)
	const FQuat HeadDelta = PoseCS[Bones.Head].GetRotation() * RefCS[Bones.Head].GetRotation().Inverse();
	const FVector HeadBase = PoseCS[Bones.Head].GetLocation();
	const FQuat ToMeshForward(FVector(0, 0, 1), FMath::DegreesToRadians(90.0));
	Helmet->SetRelativeLocationAndRotation(HeadBase + HeadDelta.RotateVector(FVector(0.0, 0.0, 7.0)), HeadDelta * ToMeshForward);
	Helmet->SetRelativeScale3D(FVector(1.0));
	Glasses->SetRelativeLocationAndRotation(HeadBase + HeadDelta.RotateVector(FVector(0.0, 2.5, 6.5)), HeadDelta * ToMeshForward);
	Glasses->SetRelativeScale3D(FVector(1.0));

	// Yerel uzaya yaz
	for (int32 I = 0; I < Num; ++I)
	{
		const int32 P = Parent[I];
		Body->BoneSpaceTransforms[I] = P >= 0 ? PoseCS[I].GetRelativeTransform(PoseCS[P]) : PoseCS[I];
	}
	if (Face->GetSkeletalMeshAsset())
	{
		// Sporcu yapisi: bel ve karin incelir, omuz hizasinda (spine_05) olcek geri alinir
		const double Slim = 0.86;
		Body->BoneSpaceTransforms[Bones.Spine[1]].SetScale3D(FVector(1.0, Slim, Slim));
		Body->BoneSpaceTransforms[Bones.Spine[4]].SetScale3D(FVector(1.0, 1.0 / Slim, 1.0 / Slim));
	}
	Body->MarkRefreshTransformDirty();
}

void AKapadokyaRider::SetupPlayerInputComponent(UInputComponent* Input)
{
	Super::SetupPlayerInputComponent(Input);
	Input->BindAxis(TEXT("Pedal"), this, &AKapadokyaRider::OnThrottle);
	Input->BindAxis(TEXT("BrakeAxis"), this, &AKapadokyaRider::OnBrake);
	Input->BindAxis(TEXT("SteerAxis"), this, &AKapadokyaRider::OnSteer);
	const auto Bind = [Input](const TCHAR* Name, EInputEvent Event, TFunction<void()> Fn)
	{
		FInputActionBinding B(FName(Name), Event);
		B.ActionDelegate.GetDelegateForManualSet().BindLambda(MoveTemp(Fn));
		Input->AddActionBinding(MoveTemp(B));
	};
	Bind(TEXT("Sprint"), IE_Pressed, [this] { bInSprint = true; });
	Bind(TEXT("Sprint"), IE_Released, [this] { bInSprint = false; });
	Bind(TEXT("Tuck"), IE_Pressed, [this] { bInTuck = true; });
	Bind(TEXT("Tuck"), IE_Released, [this] { bInTuck = false; });
	Bind(TEXT("GearUp"), IE_Pressed, [this] { bManualGears = true; PendingGear = 1; });
	Bind(TEXT("GearDown"), IE_Pressed, [this] { bManualGears = true; PendingGear = -1; });
	Bind(TEXT("AutoGear"), IE_Pressed, [this] { bManualGears = false; });
	Bind(TEXT("CameraNext"), IE_Pressed, [this] { CycleCamera(); });
}

void AKapadokyaRider::CycleCamera()
{
	CameraMode = EKCameraMode((int32(CameraMode) + 1) % int32(EKCameraMode::Count));
	bCamInit = false;
}

void AKapadokyaRider::UpdatePlayerInput(float Dt, FBikeInput& Out)
{
	// Klavye dijital: dereceli hale getir
	const double Attack = FMath::Abs(InSteer) > 0.01 ? 2.6 : 5.0;
	SmoothSteer = FMath::FInterpTo(SmoothSteer, double(InSteer), double(Dt), Attack);
	SmoothThrottle = FMath::FInterpTo(SmoothThrottle, double(InThrottle), double(Dt), 2.2);
	Out.Effort = SmoothThrottle * 1.05;
	Out.Sprint = bInSprint && InThrottle > 0.1 ? 1.0 : 0.0;
	Out.Brake = InBrake;
	Out.Lean = SmoothSteer;
	Out.bTuck = bInTuck;
	Out.bAutoGear = !bManualGears;
	Out.GearDelta = PendingGear;
	PendingGear = 0;

	if (bAssist)
	{
		// Surus yardimi: yol kavisi otomatik izlenir, oyuncu cizgiyi kaydirir; yatis tutus sinirinda kalir
		const FKapadokyaTrack& T = FKapadokyaTrack::Get();
		const double V = FMath::Max(Bike.State.Speed, 0.5);
		const double RoadHalf = FMath::Max(T.HalfWidthAt(TrackS) - 70.0, 60.0);
		// Tuslar hedef seridi kaydirir; serit yol icinde kalir
		AssistLane = FMath::Clamp(AssistLane + SmoothSteer * 240.0 * Dt, -RoadHalf, RoadHalf);
		const double WantLat = LaneFollowAccel(AssistLane);
		const double LeanLimit = FMath::Atan(0.62);
		const double MaxLean = FMath::Min(FMath::DegreesToRadians(Bike.Params.MaxLeanDeg), FMath::Atan(0.85) * 1.08);
		Out.Lean = FMath::Clamp(FMath::Atan(WantLat / 9.81), -LeanLimit, LeanLimit) / MaxLean;
		// Fren yardimi: viraja fazla hizli giriliyorsa
		const double SafeV = SafeSpeedAhead() * 1.08;
		if (V > SafeV)
		{
			Out.Brake = FMath::Max(Out.Brake, FMath::Clamp((V - SafeV) * 0.6, 0.0, 0.7));
			Out.Sprint = 0.0;
		}
	}
}

double AKapadokyaRider::LaneFollowAccel(double LaneCm) const
{
	// Serit izleme: yanal hata + yon hatasi. Yatisin gecikmesi kadar ileri kestirilir, yoksa bisiklet salinir.
	// Benzetim (3 m serit degisimi, 5-16 m/s): asma 8 cm, oturma 2.5 sn. Eski takipci hic oturmuyordu.
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	const double V = FMath::Max(Bike.State.Speed, 1.5);
	const FVector Tan = T.TangentAt(TrackS);
	const double HeadErr = FMath::UnwindRadians(Bike.State.Heading - FMath::Atan2(Tan.Y, Tan.X));
	const double KappaNow = T.CurvatureAt(TrackS) * 100.0;
	const double YawErrRate = 9.81 * FMath::Tan(Bike.State.Lean) / V - V * KappaNow;
	const double Predicted = HeadErr + 0.4 * YawErrRate;
	const double Feed = V * V * T.CurvatureAt(TrackS + V * 25.0) * 100.0;
	return Feed + 1.5 * (LaneCm - Lateral) / 100.0 - 2.4 * V * FMath::Sin(Predicted);
}

double AKapadokyaRider::SafeSpeedAhead() const
{
	// Viraj hiz siniri: ileriye dogru tara
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	double SafeV = 40.0;
	const double Mu = 0.74;
	for (double Dist = 0.0; Dist < 16000.0; Dist += 400.0)
	{
		const double K = FMath::Abs(T.CurvatureAt(TrackS + Dist)) * 100.0;
		if (K > 1e-4)
		{
			const double VCorner = FMath::Sqrt(Mu * 9.81 * 0.62 / K);
			const double VAllowed = FMath::Sqrt(VCorner * VCorner + 2.0 * 3.2 * Dist / 100.0);
			SafeV = FMath::Min(SafeV, VAllowed);
		}
	}
	return SafeV;
}

void AKapadokyaRider::UpdateAI(float Dt, FBikeInput& Out)
{
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	const double V = FMath::Max(Bike.State.Speed, 0.5);
	// Hedef serit
	const double Half = FMath::Max(T.HalfWidthAt(TrackS) - 110.0, 60.0);
	double LaneWanted = FMath::Clamp(AILane + 28.0 * FMath::Sin(GetWorld()->GetTimeSeconds() * 0.21 + AISeed), -Half, Half);
	LaneWanted = FMath::Clamp(LaneWanted + PushLateral * 0.35, -Half, Half);
	// Oncedeki kazadan kac: yana gec, yer yoksa fren
	const bool bHazard = HazardDist > 0.0;
	if (bHazard)
	{
		const double Side = Lateral >= HazardLat ? 1.0 : -1.0;
		LaneWanted = FMath::Clamp(HazardLat + Side * 200.0, -Half, Half);
	}
	const double WantedLat = LaneFollowAccel(LaneWanted);
	const double WantLean = FMath::Atan(WantedLat / 9.81);
	const double MaxLean = FMath::Min(FMath::DegreesToRadians(Bike.Params.MaxLeanDeg), FMath::Atan(0.85) * 1.08);
	Out.Lean = FMath::Clamp(WantLean / MaxLean, -1.0, 1.0);

	const double SafeV = SafeSpeedAhead();
	// Tempo: esige yakin; tirmanista ve son turda atak
	const double Grade = GradeNow;
	const double Attack = 0.5 + 0.5 * FMath::Sin(GetWorld()->GetTimeSeconds() * 0.04 + AISeed);
	const double WantEffort = FMath::Clamp(0.86 + 0.08 * AIAggression + (Grade > 0.05 ? 0.05 * Attack : -0.02) + (Grade < -0.05 ? -0.7 : 0.0), 0.0, 1.15);
	AIEffortNow = FMath::FInterpTo(AIEffortNow, WantEffort, double(Dt), 0.6);
	Out.Effort = AIEffortNow;
	Out.Sprint = AIAggression > 0.95 && Bike.State.WPrime > 3000.0 ? 1.0 : 0.0;
	Out.bTuck = Grade < -0.03 || V > 15.0;
	Out.bAutoGear = true;
	if (V > SafeV)
	{
		Out.Brake = FMath::Clamp((V - SafeV) * 0.7 + 0.1, 0.0, 0.85);
		Out.Effort = 0.0;
		Out.Sprint = 0.0;
	}
	if (bHazard && FMath::Abs(Lateral - HazardLat) < 130.0)
	{
		// Yana gececek mesafe kalmadi: duracak kadar fren
		const double Need = V * V / (2.0 * FMath::Max(HazardDist / 100.0, 0.5));
		Out.Brake = FMath::Max(Out.Brake, FMath::Clamp(Need / 6.0, 0.15, 1.0));
		Out.Effort = 0.0;
		Out.Sprint = 0.0;
	}
}

void AKapadokyaRider::StartCrash(const FVector& Impulse)
{
	if (CrashTimer > 0.0 || bRespawning)
	{
		return;
	}
	CrashTimer = 4.6;
	++CrashCount;
	Bike.State.bCrashed = true;
	if (bIsPlayer && SndCrash)
	{
		UGameplayStatics::PlaySound2D(this, SndCrash);
	}
	const double H = Bike.State.Heading;
	const FVector Forward(FMath::Cos(H), FMath::Sin(H), 0.0);
	CrashBikeVel = Forward * Bike.State.Speed * 100.0 * 0.8 + Impulse;
	CrashAngVel = FVector(FMath::FRandRange(120.f, 280.f), FMath::FRandRange(-90.f, 90.f), FMath::FRandRange(-160.f, 160.f));

	// Sporcu: fizik bebegi
	USkeletalMesh* Manny = Cast<USkeletalMesh>(Body->GetSkinnedAsset());
	if (Manny && !Ragdoll)
	{
		Ragdoll = NewObject<USkeletalMeshComponent>(this);
		Ragdoll->SetSkeletalMesh(Manny);
		Ragdoll->SetWorldTransform(Body->GetComponentTransform());
		if (UPhysicsAsset* PA = Manny->GetPhysicsAsset() ? Manny->GetPhysicsAsset() : LoadObject<UPhysicsAsset>(nullptr, TEXT("/Game/Characters/Mannequins/Rigs/PA_Mannequin.PA_Mannequin")))
		{
			Ragdoll->SetPhysicsAsset(PA);
		}
		Ragdoll->SetCollisionProfileName(TEXT("Ragdoll"));
		Ragdoll->RegisterComponent();
		for (int32 I = 0; I < Ragdoll->GetNumMaterials() && BodyMID; ++I)
		{
			Ragdoll->SetMaterial(I, BodyMID);
		}
		// T-pozdan degil, o anki surus pozundan dus: simulasyon acildiktan sonra govdeleri tasi
		Ragdoll->SetAllBodiesSimulatePhysics(true);
		const TArray<FTransform>& CrashPose = Body->GetComponentSpaceTransforms();
		const FTransform BodyWorld = Body->GetComponentTransform();
		for (FBodyInstance* BI : Ragdoll->Bodies)
		{
			if (BI && BI->BodySetup.IsValid())
			{
				const int32 Bone = Body->GetBoneIndex(BI->BodySetup->BoneName);
				if (CrashPose.IsValidIndex(Bone))
				{
					BI->SetBodyTransform(CrashPose[Bone] * BodyWorld, ETeleportType::TeleportPhysics);
				}
			}
		}
		Ragdoll->WakeAllRigidBodies();
		Ragdoll->SetAllPhysicsLinearVelocity(Forward * Bike.State.Speed * 100.0 * 0.95 + Impulse + FVector(0, 0, 120.0));
		Body->SetVisibility(false, true);
		if (Face->GetSkeletalMeshAsset())
		{
			Face->AttachToComponent(Ragdoll, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
			Face->SetLeaderPoseComponent(Ragdoll);
			Face->SetVisibility(true);
		}
		if (Outfit->GetSkeletalMeshAsset())
		{
			Outfit->AttachToComponent(Ragdoll, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
			Outfit->SetLeaderPoseComponent(Ragdoll);
			Outfit->SetVisibility(true);
		}
		Helmet->SetVisibility(false);
		Glasses->SetVisibility(false);
	}

	// Fizik zemini: yol serit agi Chaos govdelerini tutmuyor (govde 30 cm alttaki araziye oturuyordu).
	// Kaza bolgesinde yolu izleyen, sadece fiziksel kutular kurulur.
	{
		const FKapadokyaTrack& CT = FKapadokyaTrack::Get();
		for (int32 K = -1; K <= 4; ++K)
		{
			const double FloorS = CT.Wrap(TrackS + K * 1500.0);
			UBoxComponent* Patch = NewObject<UBoxComponent>(this);
			Patch->SetBoxExtent(FVector(800.0, CT.HalfWidthAt(FloorS) + 200.0, 30.0));
			Patch->SetCollisionProfileName(TEXT("BlockAll"));
			Patch->SetCollisionEnabled(ECollisionEnabled::PhysicsOnly);
			Patch->SetHiddenInGame(true);
			Patch->RegisterComponent();
			const FRotator FloorRot = CT.TangentAt(FloorS).Rotation();
			const FVector FloorUp = FloorRot.Quaternion().GetUpVector();
			Patch->SetWorldLocationAndRotation(CT.PosAt(FloorS) - FloorUp * 31.0, FloorRot);
			CrashFloor.Add(Patch);
		}
	}

	// Bisiklet: gercek rijit govde olarak savrulur (surucuyle ic ice baslar, ona carpmaz)
	if (!CrashBody)
	{
		CrashBody = NewObject<UBoxComponent>(this);
		CrashBody->SetBoxExtent(FVector(82.0, 14.0, 42.0));
		CrashBody->SetCollisionProfileName(TEXT("PhysicsActor"));
		CrashBody->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Ignore);
		CrashBody->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
		CrashBody->SetHiddenInGame(true);
		CrashBody->RegisterComponent();
		CrashBody->SetWorldLocationAndRotation(LeanRoot->GetComponentLocation() + FVector(0, 0, 52.0), LeanRoot->GetComponentRotation());
		CrashBody->SetMassOverrideInKg(NAME_None, 9.0f, true);
		CrashBody->SetLinearDamping(0.12f);
		CrashBody->SetAngularDamping(0.5f);
		CrashBody->SetSimulatePhysics(true);
		CrashBody->SetPhysicsLinearVelocity(CrashBikeVel + FVector(0, 0, 90.0));
		const double Roll = FMath::FRandRange(150.0, 330.0) * (FMath::RandBool() ? 1.0 : -1.0);
		CrashBody->SetPhysicsAngularVelocityInDegrees(Forward * Roll + FVector(0, 0, FMath::FRandRange(-120.0, 120.0)));
	}
}

void AKapadokyaRider::FunLaunch()
{
	const double H = Bike.State.Heading;
	const FVector Forward(FMath::Cos(H), FMath::Sin(H), 0.0);
	if (Ragdoll)
	{
		Ragdoll->SetAllPhysicsLinearVelocity(Forward * 260.0 + FVector(FMath::FRandRange(-140.0, 140.0), FMath::FRandRange(-140.0, 140.0), 720.0), true);
	}
	if (CrashBody)
	{
		CrashBody->SetPhysicsLinearVelocity(FVector(0.0, 0.0, 420.0), true);
		CrashBody->SetPhysicsAngularVelocityInDegrees(FVector(FMath::FRandRange(-500.0, 500.0), FMath::FRandRange(-500.0, 500.0), 300.0), true);
	}
}

void AKapadokyaRider::EndCrashPhysics()
{
	if (Ragdoll)
	{
		Ragdoll->DestroyComponent();
		Ragdoll = nullptr;
	}
	if (CrashBody)
	{
		CrashBody->DestroyComponent();
		CrashBody = nullptr;
	}
	for (UBoxComponent* Patch : CrashFloor)
	{
		if (Patch)
		{
			Patch->DestroyComponent();
		}
	}
	CrashFloor.Reset();
	LeanRoot->SetRelativeRotation(FQuat::Identity);
	LeanRoot->SetRelativeLocation(FVector::ZeroVector);
	if (Face->GetSkeletalMeshAsset())
	{
		Face->AttachToComponent(Body, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
		Face->SetLeaderPoseComponent(Body);
	}
	if (Outfit->GetSkeletalMeshAsset())
	{
		Outfit->AttachToComponent(Body, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
		Outfit->SetLeaderPoseComponent(Body);
	}
	Body->SetVisibility(true, true);
	Helmet->SetVisibility(true);
	Glasses->SetVisibility(true);
}

void AKapadokyaRider::TeleportToS(double NewS, double NewTotalS, double SpeedMs)
{
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	TrackS = T.Wrap(NewS);
	TotalS = NewTotalS;
	const double Half = FMath::Max(T.HalfWidthAt(TrackS) - 110.0, 60.0);
	Lateral = FMath::Clamp(Lateral, -Half, Half);
	AssistLane = Lateral;
	Pos = T.PosAt(TrackS) + T.RightAt(TrackS) * Lateral;
	const FVector Tan = T.TangentAt(TrackS);
	Bike.State.Heading = FMath::Atan2(Tan.Y, Tan.X);
	Bike.State.Speed = SpeedMs;
	Bike.State.Lean = 0.0;
	Bike.State.LeanRate = 0.0;
	Bike.State.Steer = 0.0;
	Bike.State.GripOverTime = 0.0;
	Bike.State.bCrashed = false;
	VerticalSpeed = 0.0;
	if (CrashTimer > 0.0)
	{
		CrashTimer = 0.0;
		bRespawning = false;
		EndCrashPhysics();
	}
	bCamInit = false;
	SetActorLocation(Pos);
}

void AKapadokyaRider::Respawn()
{
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	TrackS = T.Wrap(TrackS);
	double Keep = 0.0;
	Lateral = FMath::Clamp(Lateral, -80.0, 80.0);
	AssistLane = Lateral;
	Pos = T.PosAt(TrackS) + T.RightAt(TrackS) * Lateral;
	const FVector Tan = T.TangentAt(TrackS);
	FBikeState& S = Bike.State;
	const double W = S.WPrime;
	const double Hr = S.HeartRate;
	const int32 G = S.Gear;
	S = FBikeState();
	S.WPrime = W;
	S.HeartRate = Hr;
	S.Gear = FMath::Min(G, 6);
	S.Heading = FMath::Atan2(Tan.Y, Tan.X);
	SmoothSteer = 0.0;
	CrashTimer = 0.0;
	bRespawning = false;
	EndCrashPhysics();
	bCamInit = false;
}

void AKapadokyaRider::UpdateMotion(float Dt)
{
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	FBikeState& S = Bike.State;

	if (CrashTimer > 0.0)
	{
		CrashTimer -= Dt;
		// Bisiklet fizik govdesini izler; aktor (kamera ve bolge hesabi) onunla gider
		if (CrashBody)
		{
			const FTransform BikeT = CrashBody->GetComponentTransform();
			Pos = BikeT.GetLocation() - FVector(0, 0, 52.0);
			SetActorLocation(Pos);
			LeanRoot->SetWorldLocationAndRotation(BikeT.TransformPosition(FVector(0, 0, -52.0)), BikeT.GetRotation());
		}
		if (CrashTimer <= 0.0)
		{
			double NewLat = 0.0;
			TrackS = T.Project(Pos, TrackS, &NewLat);
			Lateral = NewLat;
			Respawn();
		}
		return;
	}

	// Girdi
	FBikeInput Input;
	if (bControlsEnabled)
	{
		if (bIsPlayer && !bAutopilot)
		{
			UpdatePlayerInput(Dt, Input);
		}
		else if (bIsPlayer && bKeyboardBot)
		{
			// Test: yapay zeka kararini klavye gibi bas/birak girdiye indirger
			// Test: dikkatsiz insan. Surekli W, rastgele A/D, hic fren yok, ara sira sprint.
			const double Clock = GetWorld()->GetTimeSeconds();
			const double Wander = FMath::Sin(Clock * 0.7) + FMath::Sin(Clock * 1.9 + 1.3);
			InSteer = Wander > 1.0 ? 1.f : (Wander < -1.0 ? -1.f : 0.f);
			InThrottle = 1.f;
			InBrake = 0.f;
			bInSprint = FMath::Sin(Clock * 0.21) > 0.75;
			UpdatePlayerInput(Dt, Input);
		}
		else
		{
			UpdateAI(Dt, Input);
		}
	}
	else
	{
		Input.Brake = bFinished ? 0.2 : 1.0;
		Input.Effort = bFinished ? 0.25 : 0.0;
		if (bFinished)
		{
			UpdateAI(Dt, Input);
			Input.Effort = FMath::Min(Input.Effort, 0.35);
			Input.Sprint = 0.0;
		}
	}

	// Yuzey
	double NewLat = 0.0;
	TrackS = T.Project(Pos, TrackS, &NewLat);
	const double Half = T.HalfWidthAt(TrackS);
	bOffRoad = FMath::Abs(NewLat) > Half + 60.0;
	CurrentSurface = T.SurfaceAt(TrackS);
	FBikeEnvironment Env;
	if (bOffRoad)
	{
		// Banket affedici: yolun hemen disi hala surulebilir
		const double OffBy = FMath::Abs(NewLat) - (Half + 60.0);
		Env.Mu = FMath::GetMappedRangeValueClamped(FVector2D(0.0, 300.0), FVector2D(0.72, 0.5), OffBy);
		Env.Crr = 0.028;
	}
	else
	{
		switch (CurrentSurface)
		{
		case 1: Env.Mu = 0.62; Env.Crr = 0.0115; break;
		case 2: Env.Mu = 0.74; Env.Crr = 0.0058; break;
		default: Env.Mu = 0.85; Env.Crr = 0.0042; break;
		}
	}
	Lateral = NewLat;

	// Zemin ve egim: iki tekerlek izi
	const double Sh = S.Heading;
	const FVector Forward(FMath::Cos(Sh), FMath::Sin(Sh), 0.0);
	const auto Ground = [this](const FVector& P, double Fallback)
	{
		FHitResult Hit;
		FCollisionQueryParams QP;
		QP.AddIgnoredActor(this);
		const FVector From(P.X, P.Y, P.Z + 300.0);
		const FVector To(P.X, P.Y, P.Z - 1200.0);
		return GetWorld()->LineTraceSingleByChannel(Hit, From, To, ECC_WorldStatic, QP) ? Hit.Location.Z : Fallback;
	};
	const FVector Base = Pos;
	const double ZF = Ground(Base + Forward * 58.0, Base.Z);
	const double ZR = Ground(Base - Forward * 40.0, Base.Z);
	const double TargetZ = (ZF * 40.0 + ZR * 58.0) / 98.0;
	double Grade = (ZF - ZR) / 98.0;
	// Uzak rakip: parkur egimine geri dus (zemin ayni)
	GradeNow = FMath::FInterpTo(GradeNow, Grade, double(Dt), 6.0);
	Env.Grade = GradeNow;
	Env.DraftFactor = DraftFactor;

	Bike.Step(Dt, Input, Env);
	if (S.bCrashed && CrashTimer <= 0.0)
	{
		StartCrash(FVector::ZeroVector);
		return;
	}

	// Oyuncu tuslari icin
	if (bIsPlayer && LastGear != S.Gear)
	{
		if (LastGear >= 0 && SndShift)
		{
			UGameplayStatics::PlaySound2D(this, SndShift, 0.7f);
		}
		LastGear = S.Gear;
	}

	// Konum
	const double SpeedCm = S.Speed * 100.0;
	const double Hdg = S.Heading;
	const FVector Move = FVector(FMath::Cos(Hdg), FMath::Sin(Hdg), 0.0) * SpeedCm * Dt + FVector(FMath::Cos(Hdg + UE_DOUBLE_PI / 2.0), FMath::Sin(Hdg + UE_DOUBLE_PI / 2.0), 0.0) * S.SlipOffset * 100.0 * Dt;
	FVector Next = Pos + Move;

	// Carpisma (oyuncu): duvar/kaya/bina
	if (bIsPlayer && SpeedCm > 50.0)
	{
		FHitResult Hit;
		FCollisionQueryParams QP;
		QP.AddIgnoredActor(this);
		const FVector Ahead(Pos.X, Pos.Y, Pos.Z + 85.0);
		const FVector AheadTo(Next.X + Forward.X * 60.0, Next.Y + Forward.Y * 60.0, Next.Z + 85.0);
		if (GetWorld()->SweepSingleByChannel(Hit, Ahead, AheadTo, FQuat::Identity, ECC_WorldStatic, FCollisionShape::MakeSphere(28.f), QP)
			&& Hit.ImpactNormal.Z < 0.55)
		{
			// Sig acili temas: surtunup sekme; kafa kafaya: dusme
			const double HeadOn = FMath::Abs(FVector::DotProduct(Forward, Hit.ImpactNormal));
			if (S.Speed > 7.0 && HeadOn > 0.55)
			{
				StartCrash(Hit.ImpactNormal * 180.0);
				return;
			}
			if (HeadOn <= 0.55)
			{
				S.Speed *= FMath::Max(0.0, 1.0 - 0.8 * double(Dt));
				const FVector Slide = FVector(Hit.ImpactNormal.X, Hit.ImpactNormal.Y, 0.0).GetSafeNormal();
				S.Heading += FMath::Clamp(FMath::UnwindRadians(FMath::Atan2(Slide.Y, Slide.X) - S.Heading), -1.0, 1.0) * 2.0 * Dt;
				Next += Slide * 60.0 * Dt;
				AssistLane -= FVector::DotProduct(Slide, FVector(FMath::Cos(Hdg + UE_DOUBLE_PI / 2.0), FMath::Sin(Hdg + UE_DOUBLE_PI / 2.0), 0.0)) * -120.0 * Dt;
			}
			else
			{
				// Dusuk hiz: sekme
				S.Speed *= 0.45;
				Next = Pos + Hit.ImpactNormal * 30.0;
			}
		}
	}
	// Sporcular arasi itis: yanal kaydirma
	if (FMath::Abs(PushLateral) > 1.0)
	{
		const FVector Right(FMath::Cos(Hdg + UE_DOUBLE_PI / 2.0), FMath::Sin(Hdg + UE_DOUBLE_PI / 2.0), 0.0);
		Next += Right * PushLateral * Dt;
	}
	Pos.X = Next.X;
	Pos.Y = Next.Y;

	// Dikey: yere otur, kucuk tumseklerde hafif sekme
	if (Pos.Z > TargetZ + 3.0)
	{
		VerticalSpeed -= 980.0 * Dt;
		Pos.Z = FMath::Max(TargetZ, Pos.Z + VerticalSpeed * Dt);
		if (Pos.Z <= TargetZ)
		{
			VerticalSpeed = 0.0;
		}
	}
	else
	{
		VerticalSpeed = (TargetZ - Pos.Z) / FMath::Max(double(Dt), 0.001);
		Pos.Z = TargetZ;
		VerticalSpeed = FMath::Clamp(VerticalSpeed, -400.0, 400.0);
	}

	// Sinir: yoldan cok uzaklasan oyuncu yola doner
	if (FMath::Abs(Lateral) > Half + 3500.0 || Pos.Z < T.WaterZ - 50.0)
	{
		bRespawning = true;
		Lateral = FMath::Sign(Lateral) * 60.0;
		Respawn();
		return;
	}

	// Gorsel: yatis, gidon, tekerlek, krank, baglanti noktalari
	PitchRad = FMath::Atan(GradeNow);
	const FRotator Facing(FMath::RadiansToDegrees(PitchRad), FMath::RadiansToDegrees(S.Heading), 0.0);
	SetActorLocationAndRotation(Pos, Facing);
	const double LeanDeg = FMath::RadiansToDegrees(S.Lean);
	LeanRoot->SetRelativeRotation(FRotator(0.0, 0.0, LeanDeg));

	const FVector SteerAxisLocal = (HeadTop - HeadPivot).GetSafeNormal();
	SteerPivot->SetRelativeRotation(FQuat(SteerAxisLocal, S.Steer));
	const FQuat WheelQ(FVector(0, 1, 0), S.WheelAngle);
	FrontWheel->SetRelativeRotation(WheelQ);
	RearWheel->SetRelativeRotation(WheelQ);
	CrankMesh->SetRelativeRotation(FQuat(FVector(0, 1, 0), S.CrankAngle));
	const double A = S.CrankAngle;
	PedalR->SetRelativeLocation(BB + FVector(FMath::Cos(A) * CrankLen, PedalY, -FMath::Sin(A) * CrankLen));
	PedalL->SetRelativeLocation(BB + FVector(-FMath::Cos(A) * CrankLen, -PedalY, FMath::Sin(A) * CrankLen));
}

void AKapadokyaRider::UpdateCamera(float Dt)
{
	const FBikeState& S = Bike.State;
	const double H = S.Heading;
	const FVector Forward(FMath::Cos(H), FMath::Sin(H), 0.0);
	const FVector Right(-Forward.Y, Forward.X, 0.0);
	const double SpeedK = FMath::Clamp(S.Speed / 18.0, 0.0, 1.0);
	FVector Want;
	double FovWant = 75.0;
	FVector Focus = Pos + FVector(0, 0, 118.0);
	double RollWant = 0.0;
	double Rate = 10.0;
	switch (CameraMode)
	{
	case EKCameraMode::Chase:
		Want = Pos - Forward * (410.0 + 90.0 * SpeedK) + FVector(0, 0, 195.0 + 18.0 * SpeedK) - Right * S.Lean * 50.0;
		Focus = Pos + Forward * 260.0 + FVector(0, 0, 90.0);
		FovWant = 72.0 + 16.0 * SpeedK;
		RollWant = FMath::RadiansToDegrees(S.Lean) * 0.22;
		break;
	case EKCameraMode::Near:
		Want = Pos - Forward * 230.0 + Right * 45.0 * FMath::Sin(S.Lean * 0.5) + FVector(0, 0, 125.0);
		Focus = Pos + Forward * 180.0 + FVector(0, 0, 105.0);
		FovWant = 70.0 + 18.0 * SpeedK;
		RollWant = FMath::RadiansToDegrees(S.Lean) * 0.4;
		Rate = 14.0;
		break;
	case EKCameraMode::Bars:
		Want = Pos + Forward * 22.0 + FVector(0, 0, 155.0) + Right * FMath::Sin(S.Lean) * 42.0;
		Focus = Pos + Forward * 1000.0 + FVector(0, 0, 90.0);
		FovWant = 86.0 + 10.0 * SpeedK;
		RollWant = FMath::RadiansToDegrees(S.Lean) * 0.75;
		Rate = 30.0;
		break;
	default:
		// Yayin: yol kenari, sabit kamera. Uzaklasinca siradaki noktaya atlar.
		if (!bCamInit || FVector::Dist(BroadcastAnchor, Pos) > 7000.0)
		{
			const FKapadokyaTrack& T = FKapadokyaTrack::Get();
			const double Sa = TrackS + 3800.0;
			const double Side = (FMath::RandBool() ? 1.0 : -1.0);
			BroadcastAnchor = T.PosAt(Sa) + T.RightAt(Sa) * Side * (T.HalfWidthAt(Sa) + 25.0) + FVector(0, 0, 210.0);
			CamPos = BroadcastAnchor;
		}
		Want = BroadcastAnchor;
		Focus = Pos + FVector(0, 0, 95.0) + Forward * S.Speed * 20.0;
		FovWant = FMath::Clamp(FVector::Dist(BroadcastAnchor, Pos) * 0.012, 20.0, 55.0);
		Rate = 30.0;
		break;
	}
	// Kazada kamera sporcuyu izler
	if (CrashTimer > 0.0 && Ragdoll)
	{
		Focus = Ragdoll->GetSocketLocation(TEXT("pelvis"));
	}
	// Bozuk zemin titremesi
	const double SurfaceShake = CurrentSurface == 1 ? 1.0 : (CurrentSurface == 2 ? 0.28 : 0.05);
	ShakeEnergy = FMath::FInterpTo(ShakeEnergy, bOffRoad ? 1.6 : SurfaceShake, double(Dt), 5.0);
	ShakeT += Dt * (18.0 + S.Speed * 2.2);
	const double ShakeAmp = ShakeEnergy * FMath::Clamp(S.Speed / 11.0, 0.0, 1.2) * (CameraMode == EKCameraMode::Bars ? 1.7 : 0.8);
	FVector Shake = FVector(FMath::PerlinNoise1D(ShakeT * 0.7), FMath::PerlinNoise1D(ShakeT * 0.9 + 9.0), FMath::PerlinNoise1D(ShakeT * 1.3 + 21.0)) * ShakeAmp * 3.2;

	if (!bCamInit)
	{
		CamPos = Want;
		CamFov = FovWant;
		bCamInit = true;
	}
	CamPos = FMath::VInterpTo(CamPos, Want, Dt, Rate);
	// Kamera arazinin altina inmesin
	FHitResult Hit;
	FCollisionQueryParams QP;
	QP.AddIgnoredActor(this);
	if (GetWorld()->LineTraceSingleByChannel(Hit, CamPos + FVector(0, 0, 400.0), CamPos - FVector(0, 0, 60.0), ECC_WorldStatic, QP))
	{
		CamPos.Z = FMath::Max(CamPos.Z, Hit.Location.Z + 55.0);
	}
	CamFov = FMath::FInterpTo(CamFov, FovWant, double(Dt), 3.0);
	CamRoll = FMath::FInterpTo(CamRoll, RollWant, double(Dt), 5.0);
	const FVector Eye = CamPos + Shake;
	FRotator Rot = (Focus - Eye).Rotation();
	Rot.Roll = CamRoll;
	Camera->SetWorldLocationAndRotation(Eye, Rot);
	Camera->SetFieldOfView(CamFov);
}

void AKapadokyaRider::UpdateAudio(float Dt)
{
	const FBikeState& S = Bike.State;
	const double V = S.Speed;
	if (SndTyre)
	{
		SndTyre->SetVolumeMultiplier(FMath::Clamp(V / 14.0, 0.0, 1.0));
		SndTyre->SetPitchMultiplier(0.7 + V / 22.0);
	}
	if (SndWind)
	{
		SndWind->SetVolumeMultiplier(FMath::Clamp((V - 3.0) / 18.0, 0.0, 1.0) * 1.1);
		SndWind->SetPitchMultiplier(0.8 + V / 26.0);
	}
	if (SndFreewheel)
	{
		const bool bCoasting = S.Power < 12.0 && V > 2.0;
		SndFreewheel->SetVolumeMultiplier(bCoasting ? FMath::Clamp(V / 8.0, 0.2, 0.75) : 0.0);
		SndFreewheel->SetPitchMultiplier(0.45 + V / 12.0);
	}
	if (SndChain)
	{
		SndChain->SetVolumeMultiplier(S.Power > 12.0 ? FMath::Clamp(S.Power / 520.0, 0.08, 0.5) : 0.0);
		SndChain->SetPitchMultiplier(FMath::Clamp(S.Cadence / 90.0, 0.5, 1.5));
	}
	if (SndCobble)
	{
		const double On = (CurrentSurface == 1 || bOffRoad) ? 1.0 : 0.0;
		SndCobble->SetVolumeMultiplier(On * FMath::Clamp(V / 10.0, 0.0, 1.0));
		SndCobble->SetPitchMultiplier(0.75 + V / 24.0);
	}
	if (SndBreath)
	{
		const double Effort = FMath::Clamp((S.HeartRate - 130.0) / 55.0, 0.0, 1.0);
		SndBreath->SetVolumeMultiplier(Effort * 0.6);
		SndBreath->SetPitchMultiplier(0.85 + Effort * 0.4);
	}
}

double AKapadokyaRider::ShadowNearM = 1000.0;

void AKapadokyaRider::ApplyTeamToJersey()
{
	if (JerseyMID)
	{
		JerseyMID->SetVectorParameterValue(TEXT("Jersey"), JerseyA);
		JerseyMID->SetVectorParameterValue(TEXT("Jersey2"), JerseyB);
	}
}

void AKapadokyaRider::UpdateShadowLod(float Dt)
{
	// Olcum: Nanite olmayan bisiklet ve mankenler gunes golgesinde 2-4 ms. Uzaktakiler golge atmaz.
	ShadowClock -= Dt;
	if (ShadowClock > 0.f)
	{
		return;
	}
	ShadowClock = 0.3f;
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	if (!PC || !PC->PlayerCameraManager)
	{
		return;
	}
	const double D = FVector::Dist(PC->PlayerCameraManager->GetCameraLocation(), GetActorLocation()) / 100.0;
	// Uzak sporcular daha az koseli modele gecer (LOD, 0: otomatik)
	// Forced: 0 otomatik, N = LOD N-1. Gomlek inceltme kemigi LOD0'da; 30 m'ye kadar yakin LOD kalir.
	// Esik payi: esikte gidip gelen sporcu render durumunu her seferinde yeniden kurmasin (takilma)
	const double LodHyst = ForcedLod == 1 ? 6.0 : (ForcedLod == 2 ? -6.0 : 0.0);
	const int32 WantLod = bIsPlayer ? 1 : (D < 30.0 + LodHyst ? 1 : (D < 70.0 + LodHyst ? 2 : 3));
	if (WantLod != ForcedLod)
	{
		ForcedLod = WantLod;
		Body->SetForcedLOD(WantLod);
		Face->SetForcedLOD(WantLod);
		Outfit->SetForcedLOD(WantLod);
	}
	const double ShadowHyst = ShadowLevel >= 1 ? 3.0 : 0.0;
	const int32 Level = (bIsPlayer || D < ShadowNearM + ShadowHyst) ? 2 : (D < ShadowNearM * 2.0 + ShadowHyst ? 1 : 0);
	if (Level == ShadowLevel)
	{
		return;
	}
	ShadowLevel = Level;
	Body->SetCastShadow(Level >= 2);
	Outfit->SetCastShadow(Level >= 1);
	Face->SetCastShadow(false);
	FrameMesh->SetCastShadow(Level >= 1);
	for (UStaticMeshComponent* C : { FrontWheel.Get(), RearWheel.Get() })
	{
		C->SetCastShadow(Level >= 2);
	}
	for (UStaticMeshComponent* C : { SteerMesh.Get(), CrankMesh.Get(), PedalR.Get(), PedalL.Get(), Glasses.Get() })
	{
		C->SetCastShadow(Level >= 2 && ShadowNearM > 100.0);
	}
	Helmet->SetCastShadow(Level >= 2);
}

void AKapadokyaRider::Tick(float DeltaSeconds)
{
	UpdateShadowLod(DeltaSeconds);
	Super::Tick(DeltaSeconds);
	const float Dt = FMath::Min(DeltaSeconds, 0.12f);
	UpdateMotion(Dt);
	if (CrashTimer <= 0.0 && Body->IsVisible())
	{
		UpdatePose(Dt);
	}
	if (bIsPlayer)
	{
		UpdateCamera(Dt);
		UpdateAudio(Dt);
	}
}
