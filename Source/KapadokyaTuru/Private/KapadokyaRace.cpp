#include "KapadokyaRace.h"
#include "RHI.h"
#include "RHIStats.h"
#include "KapadokyaRider.h"
#include "KapadokyaTrack.h"
#include "KapadokyaWorld.h"
#include "Components/AudioComponent.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Misc/App.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameUserSettings.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/PlatformMisc.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Sound/SoundBase.h"

namespace
{
	struct FTeam { const TCHAR* Name; FLinearColor A; FLinearColor B; };
	const FTeam Teams[] = {
		{ TEXT("Peri Spor"), FLinearColor(0.72f, 0.02f, 0.03f), FLinearColor(0.9f, 0.9f, 0.9f) },
		{ TEXT("Erciyes Pro"), FLinearColor(0.02f, 0.10f, 0.42f), FLinearColor(0.85f, 0.75f, 0.2f) },
		{ TEXT("Kızılırmak BK"), FLinearColor(0.35f, 0.05f, 0.03f), FLinearColor(0.85f, 0.45f, 0.15f) },
		{ TEXT("Selçuklu Takımı"), FLinearColor(0.02f, 0.22f, 0.20f), FLinearColor(0.75f, 0.62f, 0.25f) },
	};
	const TCHAR* Names[] = {
		TEXT("Sen"), TEXT("Cemal Toprak"), TEXT("Baran Ateş"), TEXT("Ozan Kıraç"), TEXT("Tufan Erdem"), TEXT("Kerem Sarı"),
		TEXT("Yiğit Akın"), TEXT("Alper Duman"), TEXT("Serkan Bulut"), TEXT("Umut Yalçın"), TEXT("Levent Keskin"), TEXT("Rıza Tan"),
		TEXT("Doruk Çetin"), TEXT("Emre Soylu"), TEXT("Hakan Bora"), TEXT("Volkan İnce"),
	};

	USoundBase* LoadSnd(const TCHAR* Name)
	{
		return LoadObject<USoundBase>(nullptr, *FString::Printf(TEXT("/Game/Kapadokya/Audio/%s.%s"), Name, Name));
	}
}

AKapadokyaRace::AKapadokyaRace()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bTickEvenWhenPaused = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AKapadokyaRace::BeginPlay()
{
	Super::BeginPlay();
	SndBeep = LoadSnd(TEXT("S_Beep"));
	SndGo = LoadSnd(TEXT("S_Go"));
	SndFanfare = LoadSnd(TEXT("S_Fanfare"));
	if (USoundBase* M = LoadSnd(TEXT("S_Music")))
	{
		Music = UGameplayStatics::SpawnSound2D(this, M, 0.55f);
	}
	if (USoundBase* C = LoadSnd(TEXT("S_Crowd")))
	{
		Crowd = UGameplayStatics::SpawnSound2D(this, C, 0.0f);
	}
}

void AKapadokyaRace::Setup(AKapadokyaWorld* InWorld)
{
	World = InWorld;
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	// Zirve puani: kale bolgesi baslangici
	const int32 KaleZone = T.ZoneTitles.IndexOfByKey(TEXT("Kale Zirvesi"));
	for (int32 I = 0; I < T.Points.Num(); ++I)
	{
		if (T.Zone[I] == KaleZone)
		{
			KomS = I * T.Step;
			break;
		}
	}
	bAuto = FParse::Param(FCommandLine::Get(), TEXT("KAuto"));
	BuildMenu(false);
	// Oyuncu baslangic sahnesinde menude de dursun
	if (bAuto)
	{
		FParse::Value(FCommandLine::Get(), TEXT("-KLaps="), Laps);
		FParse::Value(FCommandLine::Get(), TEXT("-KDiff="), Difficulty);
		StartRace();
	}
	else
	{
		StartRace();
		State = EKRaceState::Menu;
		for (AKapadokyaRider* R : Riders)
		{
			R->bControlsEnabled = false;
		}
	}
}

void AKapadokyaRace::BuildMenu(bool bPause)
{
	bPausedMenu = bPause;
	Menu.Reset();
	MenuIndex = 0;
	Menu.Add({ bPause ? TEXT("Devam Et") : TEXT("YARIŞA BAŞLA"), {}, 0 });
	if (!bPause)
	{
		Menu.Add({ TEXT("Tur"), { TEXT("1 tur (7,5 km)"), TEXT("2 tur (15 km)"), TEXT("3 tur (22 km)") }, FMath::Clamp(Laps - 1, 0, 2) });
		Menu.Add({ TEXT("Zorluk"), { TEXT("Amatör"), TEXT("Profesyonel"), TEXT("Tur Şampiyonu") }, Difficulty });
		Menu.Add({ TEXT("Sürüş Yardımı"), { TEXT("Açık"), TEXT("Kapalı") }, bAssist ? 0 : 1 });
		Menu.Add({ TEXT("Mod"), { TEXT("Eğlence"), TEXT("Ciddi") }, bFunMode ? 0 : 1 });
	}
	Menu.Add({ TEXT("Gün Işığı"), { TEXT("Gün Doğumu"), TEXT("Öğle"), TEXT("Gün Batımı") }, World ? int32(World->GetTimeOfDay()) : 0 });
	Menu.Add({ TEXT("Grafik"), { TEXT("Düşük"), TEXT("Orta"), TEXT("Yüksek"), TEXT("Sinematik") }, World ? World->GetQuality() : 1 });
	Menu.Add({ bPause ? TEXT("Yeniden Başlat") : TEXT("Çıkış"), {}, 0 });
	if (bPause)
	{
		Menu.Add({ TEXT("Çıkış"), {}, 0 });
	}
}

void AKapadokyaRace::MenuMove(int32 Delta)
{
	if (Menu.Num() > 0 && (State == EKRaceState::Menu || State == EKRaceState::Paused))
	{
		MenuIndex = (MenuIndex + Delta + Menu.Num()) % Menu.Num();
	}
}

void AKapadokyaRace::MenuChange(int32 Delta)
{
	if (State != EKRaceState::Menu && State != EKRaceState::Paused)
	{
		return;
	}
	FKMenuItem& Item = Menu[MenuIndex];
	if (Item.Options.Num() > 0)
	{
		Item.Value = (Item.Value + Delta + Item.Options.Num()) % Item.Options.Num();
		ApplySettings();
	}
}

void AKapadokyaRace::ApplySettings()
{
	for (const FKMenuItem& I : Menu)
	{
		if (I.Label == TEXT("Tur"))
		{
			Laps = I.Value + 1;
		}
		else if (I.Label == TEXT("Zorluk"))
		{
			Difficulty = I.Value;
		}
		else if (I.Label == TEXT("Mod"))
		{
			bFunMode = I.Value == 0;
		}
		else if (I.Label == TEXT("Sürüş Yardımı"))
		{
			bAssist = I.Value == 0;
			if (Player)
			{
				Player->bAssist = bAssist;
			}
		}
		else if (I.Label == TEXT("Gün Işığı") && World && int32(World->GetTimeOfDay()) != I.Value)
		{
			World->ApplyTimeOfDay(EKTimeOfDay(I.Value));
		}
		else if (I.Label == TEXT("Grafik") && World && World->GetQuality() != I.Value)
		{
			World->ApplyQuality(I.Value);
		}
	}
}

void AKapadokyaRace::MenuConfirm()
{
	if (State == EKRaceState::Results)
	{
		UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)));
		return;
	}
	if (State != EKRaceState::Menu && State != EKRaceState::Paused)
	{
		return;
	}
	const FString& L = Menu[MenuIndex].Label;
	if (L == TEXT("YARIŞA BAŞLA"))
	{
		ApplySettings();
		StartRace();
	}
	else if (L == TEXT("Devam Et"))
	{
		TogglePause();
	}
	else if (L == TEXT("Yeniden Başlat"))
	{
		UGameplayStatics::SetGamePaused(this, false);
		UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)));
	}
	else if (L == TEXT("Çıkış"))
	{
		FPlatformMisc::RequestExit(false, TEXT("Menuden cikis"));
	}
}

void AKapadokyaRace::TogglePause()
{
	if (State == EKRaceState::Paused)
	{
		State = EKRaceState::Racing;
		UGameplayStatics::SetGamePaused(this, false);
	}
	else if (State == EKRaceState::Racing)
	{
		State = EKRaceState::Paused;
		BuildMenu(true);
		UGameplayStatics::SetGamePaused(this, true);
	}
}

void AKapadokyaRace::StartRace()
{
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	RaceDistance = Laps * T.Length;
	for (AKapadokyaRider* R : Riders)
	{
		R->Destroy();
	}
	Riders.Reset();
	const double Strengths[3][2] = { { 0.72, 0.84 }, { 0.84, 0.97 }, { 0.94, 1.06 } };
	const double* Band = Strengths[FMath::Clamp(Difficulty, 0, 2)];
	FParse::Value(FCommandLine::Get(), TEXT("-KRiders="), RiderCount);
	RiderCount = FMath::Clamp(RiderCount, 1, 16);
	for (int32 I = 0; I < RiderCount; ++I)
	{
		const int32 Row = I / 3;
		const int32 Col = I % 3;
		const double S = StartLineS - 200.0 - Row * 280.0;
		const double Lat = (Col - 1) * 130.0;
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		AKapadokyaRider* R = GetWorld()->SpawnActor<AKapadokyaRider>(AKapadokyaRider::StaticClass(), FTransform::Identity, Params);
		const FTeam& Team = Teams[I % UE_ARRAY_COUNT(Teams)];
		const bool bIsPlayer = I == RiderCount / 2;
		const double Strength = FMath::Lerp(Band[0], Band[1], double(I) / FMath::Max(RiderCount - 1, 1));
		R->InitRider(I, bIsPlayer ? Names[0] : Names[I + 1], Team.Name, Team.A, Team.B, bIsPlayer, S, Lat, Strength);
		R->SetAIAggression(FMath::FRandRange(0.2f, 0.85f));
		R->bAutopilot = bIsPlayer && (bAuto || FParse::Param(FCommandLine::Get(), TEXT("KMenuAuto")));
		R->bKeyboardBot = R->bAutopilot && FParse::Param(FCommandLine::Get(), TEXT("KKeyBot"));
		R->bAssist = bAssist && !FParse::Param(FCommandLine::Get(), TEXT("KNoAssist"));
		Riders.Add(R);
		if (bIsPlayer)
		{
			Player = R;
		}
	}
	PrevS.Init(0.0, Riders.Num());
	for (int32 I = 0; I < Riders.Num(); ++I)
	{
		PrevS[I] = Riders[I]->TrackS;
		Riders[I]->TotalS = Riders[I]->TrackS - StartLineS;
	}
	KomAwarded.Init(0, Laps + 1);
	SprintAwarded.Init(0, Laps + 1);
	FinishedCount = 0;
	FinishDelay = -1.0;
	RaceTime = 0.0;
	Countdown = 5.0;
	LastBeep = -1;
	SpawnFun();
	State = EKRaceState::Countdown;
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		PC->Possess(Player);
		PC->SetViewTarget(Player);
	}
	if (Music)
	{
		Music->SetVolumeMultiplier(0.26f);
	}
	JumpPoints.Reset();
	JumpIndex = 0;
	FString Jumps;
	if (FParse::Value(FCommandLine::Get(), TEXT("-KJumps="), Jumps, false))
	{
		TArray<FString> Parts;
		Jumps.ParseIntoArray(Parts, TEXT(","));
		for (const FString& Part : Parts)
		{
			JumpPoints.Add(FCString::Atod(*Part));
		}
		FParse::Value(FCommandLine::Get(), TEXT("-KJumpEvery="), JumpEvery);
	}
	FString Tele;
	if (FParse::Value(FCommandLine::Get(), TEXT("-KTelemetry="), Tele))
	{
		TelemetryPath = FPaths::ProjectSavedDir() / Tele;
		FFileHelper::SaveStringToFile(TEXT("t,total_km,lap_s,speed_kmh,power,cadence,hr,wprime,gear,lean_deg,lateral_m,grade,pos,crashes,draft,fps\n"), *TelemetryPath);
	}
}

void AKapadokyaRace::Show(const FString& Text, double Seconds)
{
	Banner = Text;
	BannerTimer = Seconds;
}

void AKapadokyaRace::UpdatePack(float Dt)
{
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	const int32 N = Riders.Num();
	for (AKapadokyaRider* R : Riders)
	{
		R->PushLateral = 0.0;
		R->HazardDist = -1.0;
	}
	// Kaza zinciri: dusmus bisiklet ve sporcu yolda engeldir
	{
		const FKapadokyaTrack& Track = FKapadokyaTrack::Get();
		for (AKapadokyaRider* B : Riders)
		{
			if (B->CrashTimer <= 0.0)
			{
				continue;
			}
			double BLat = 0.0;
			const double BS = Track.Project(B->GetActorLocation(), B->TrackS, &BLat);
			for (AKapadokyaRider* A : Riders)
			{
				if (A == B || A->CrashTimer > 0.0)
				{
					continue;
				}
				double Ahead = BS - A->TrackS;
				if (Ahead < -Track.Length * 0.5)
				{
					Ahead += Track.Length;
				}
				const double Side = FMath::Abs(BLat - A->Lateral);
				if (Ahead > 0.0 && Ahead < 3500.0 && Side < 190.0 && (A->HazardDist < 0.0 || Ahead < A->HazardDist))
				{
					A->HazardDist = Ahead;
					A->HazardLat = BLat;
				}
				if (Ahead > -40.0 && Ahead < 75.0 && Side < 60.0 && A->Bike.State.Speed > 3.0)
				{
					A->StartCrash(FVector(0.0, 0.0, 80.0));
					if (A->bIsPlayer)
					{
						Show(TEXT("Kazaya takıldın!"));
					}
				}
			}
		}
	}
	for (int32 I = 0; I < N; ++I)
	{
		AKapadokyaRider* A = Riders[I];
		double Shelter = 0.0;
		int32 Sheltering = 0;
		for (int32 J = 0; J < N; ++J)
		{
			if (I == J)
			{
				continue;
			}
			AKapadokyaRider* B = Riders[J];
			const double Gap = B->TotalS - A->TotalS; // B onde ise +
			const double Dl = B->Lateral - A->Lateral;
			if (Gap > 50.0 && Gap < 1000.0 && FMath::Abs(Dl) < 80.0 + Gap * 0.08)
			{
				Shelter = FMath::Max(Shelter, 0.38 * (1.0 - Gap / 1000.0));
				++Sheltering;
			}
			// Omuz omuza: yan yana gelince acil
			if (FMath::Abs(Gap) < 200.0 && FMath::Abs(Dl) < 72.0)
			{
				const double Sign = Dl >= 0.0 ? -1.0 : 1.0;
				A->PushLateral += Sign * (72.0 - FMath::Abs(Dl)) * 2.5;
				// Oyuncu omuz temasi: gidon sarsilir, cok yakinsa tekerler dolasir
				if (A->bIsPlayer && !A->bAutopilot && FMath::Abs(Gap) < 130.0 && FMath::Abs(Dl) < 48.0 && A->CrashTimer <= 0.0)
				{
					A->Bike.State.LeanRate += Sign * 4.8 * Dt;
					A->AddAssistNudge(Sign * 90.0 * Dt);
					if (FMath::Abs(Dl) < 22.0 && FMath::Abs(Gap) < 90.0 && A->Bike.State.Speed > 6.0)
					{
						A->StartCrash(FVector(0.0, Sign * 90.0, 40.0));
						Show(TEXT("Tekerler dolaştı!"));
					}
				}
			}
			// Oyuncu: ondeki arka tekere carpma
			if (A->bIsPlayer && !A->bAutopilot && Gap > 30.0 && Gap < 120.0 && FMath::Abs(Dl) < 30.0
				&& A->Bike.State.Speed > B->Bike.State.Speed + 2.5 && A->CrashTimer <= 0.0)
			{
				A->StartCrash(FVector::ZeroVector);
				Show(TEXT("Öndeki tekere çarptın!"));
			}
		}
		A->DraftFactor = FMath::Min(0.46, Shelter + (Sheltering > 1 ? 0.02 * (Sheltering - 1) : 0.0));

		// Serit: tirmanista daha cok acik, duzlukte toplu
		const double Half = T.HalfWidthAt(A->TrackS) - 90.0;
		const double Base = A->Id % 3 == 0 ? -0.55 : (A->Id % 3 == 1 ? 0.0 : 0.55);
		A->SetLaneTarget(Base * Half);
	}
}

void AKapadokyaRace::UpdateOrder()
{
	TArray<AKapadokyaRider*> Order;
	for (AKapadokyaRider* R : Riders)
	{
		Order.Add(R);
	}
	Order.Sort([](const AKapadokyaRider& A, const AKapadokyaRider& B)
	{
		if (A.bFinished != B.bFinished)
		{
			return A.bFinished;
		}
		if (A.bFinished)
		{
			return A.FinishTime < B.FinishTime;
		}
		return A.TotalS > B.TotalS;
	});
	for (int32 I = 0; I < Order.Num(); ++I)
	{
		Order[I]->Position = I + 1;
	}
}

void AKapadokyaRace::AwardPoints()
{
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	const int32 KomPts[] = { 5, 3, 1 };
	const int32 SprPts[] = { 7, 4, 2 };
	const double KomOffset = T.Wrap(KomS - StartLineS);
	for (int32 Lap = 0; Lap < Laps; ++Lap)
	{
		// Zirve
		const double KomLine = Lap * T.Length + KomOffset;
		if (KomAwarded[Lap] < 3)
		{
			for (AKapadokyaRider* R : Riders)
			{
				if (R->TotalS >= KomLine && R->KomPoints < 1000 * (Lap + 1))
				{
					const int32 Rank = KomAwarded[Lap];
					if (Rank < 3)
					{
						R->KomPoints += KomPts[Rank] + 1000 * (Lap + 1) - (R->KomPoints / 1000) * 1000;
						KomAwarded[Lap]++;
						if (R->bIsPlayer)
						{
							Show(FString::Printf(TEXT("Zirve puanı +%d"), KomPts[Rank]));
						}
						else if (Rank == 0)
						{
							Show(FString::Printf(TEXT("Zirveyi %s geçti"), *R->RiderName));
						}
					}
				}
			}
		}
		// Ara sprint: tur sonlari
		if (Lap < Laps - 1 && SprintAwarded[Lap] < 3)
		{
			const double Line = (Lap + 1) * T.Length;
			for (AKapadokyaRider* R : Riders)
			{
				if (R->TotalS >= Line && R->SprintPoints < 1000 * (Lap + 1))
				{
					const int32 Rank = SprintAwarded[Lap];
					if (Rank < 3)
					{
						R->SprintPoints += SprPts[Rank] + 1000 * (Lap + 1) - (R->SprintPoints / 1000) * 1000;
						SprintAwarded[Lap]++;
						if (R->bIsPlayer)
						{
							Show(FString::Printf(TEXT("Ara sprint +%d"), SprPts[Rank]));
						}
					}
				}
			}
		}
	}
}

void AKapadokyaRace::Finish(AKapadokyaRider* Rider)
{
	Rider->bFinished = true;
	Rider->FinishTime = RaceTime;
	Rider->bControlsEnabled = false;
	++FinishedCount;
	if (Rider->bIsPlayer)
	{
		Show(FString::Printf(TEXT("BİTİŞ!  %d. sıra"), FinishedCount), 6.0);
		if (SndFanfare)
		{
			UGameplayStatics::PlaySound2D(this, SndFanfare);
		}
		FinishDelay = 7.0;
	}
}

void AKapadokyaRace::SpawnFun()
{
	for (UStaticMeshComponent* M : FunMeshes)
	{
		if (M)
		{
			M->DestroyComponent();
		}
	}
	FunMeshes.Reset();
	FunItems.Reset();
	TurboTime = 0.0;
	bPlayerWasCrashed = false;
	if (!bFunMode)
	{
		return;
	}
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	UStaticMesh* Meshes[] = {
		LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Kapadokya/Gen/S_brass_pot_01.S_brass_pot_01")),
		LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Kapadokya/Gen/S_wine_barrel_01.S_wine_barrel_01")),
		LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Kapadokya/Gen/S_wooden_crate_01.S_wooden_crate_01")) };
	FRandomStream Rng(1923);
	for (double Dist = 22000.0; Dist < T.Length - 8000.0; Dist += Rng.FRandRange(11000.0, 24000.0))
	{
		FKFunItem Item;
		Item.S = T.Wrap(StartLineS + Dist);
		const double Roll = Rng.FRand();
		Item.Type = Roll < 0.4 ? 0 : (Roll < 0.7 ? 1 : 2);
		const double Half = FMath::Max(T.HalfWidthAt(Item.S) - 80.0, 40.0);
		Item.Lat = Rng.FRandRange(-Half, Half);
		Item.Home = T.PosAt(Item.S) + T.RightAt(Item.S) * Item.Lat + FVector(0.0, 0.0, Item.Type == 0 ? 80.0 : 0.0);
		UStaticMesh* Mesh = Meshes[Item.Type];
		if (!Mesh)
		{
			continue;
		}
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(Mesh);
		C->SetMobility(EComponentMobility::Movable);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->RegisterComponent();
		C->SetWorldLocationAndRotation(Item.Home, FRotator(0.f, Rng.FRandRange(0.f, 360.f), 0.f));
		C->SetWorldScale3D(FVector(Item.Type == 0 ? 2.6 : (Item.Type == 2 ? 1.7 : 1.1)));
		FunMeshes.Add(C);
		FunItems.Add(Item);
	}
	UE_LOG(LogTemp, Display, TEXT("KFUN %d esya"), FunItems.Num());
}

void AKapadokyaRace::UpdateFun(float Dt)
{
	static const TCHAR* TeaJokes[] = { TEXT("Çayı içti, uçuyor!"), TEXT("Demli çay turbosu!"), TEXT("İnce belli güç verdi!") };
	static const TCHAR* HitJokes[] = { TEXT("Esnaf küstü, fıçı gitti!"), TEXT("Bisiklet gitti, sporcu yürüyor!"), TEXT("Sigorta bunu karşılamaz!"), TEXT("Havacılık tarihine geçti!"), TEXT("Kapadokya'nın en alçak balonu!") };
	if (!Player)
	{
		return;
	}
	// Kaza ani: abartili firlama ve kisa agir cekim. Cay ve kasalar Eglence modunda.
	const bool bCrashed = Player->CrashTimer > 0.0;
	if (bFunMode && bCrashed && !bPlayerWasCrashed)
	{
		Player->FunLaunch();
		Show(HitJokes[JokeIndex++ % UE_ARRAY_COUNT(HitJokes)], 3.0);
		SlowTime = 1.1;
		UGameplayStatics::SetGlobalTimeDilation(this, 0.4f);
	}
	bPlayerWasCrashed = bCrashed;
	if (SlowTime > 0.0)
	{
		SlowTime -= FApp::GetDeltaTime() / 0.4;
		if (SlowTime <= 0.0)
		{
			UGameplayStatics::SetGlobalTimeDilation(this, 1.f);
		}
	}
	if (TurboTime > 0.0 && !bCrashed)
	{
		TurboTime -= Dt;
		if (Player->Bike.State.Speed < 19.0)
		{
			Player->Bike.State.Speed += 2.8 * Dt;
		}
	}
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	const double Clock = GetWorld()->GetTimeSeconds();
	for (int32 I = 0; I < FunItems.Num(); ++I)
	{
		FKFunItem& Item = FunItems[I];
		UStaticMeshComponent* C = FunMeshes[I];
		if (Item.Hidden > 0.0)
		{
			Item.Hidden -= Dt;
			if (Item.Hidden <= 0.0)
			{
				C->SetVisibility(true);
				C->SetWorldLocation(Item.Home);
			}
			continue;
		}
		if (Item.FlyTime >= 0.0)
		{
			Item.FlyTime += Dt;
			Item.Vel.Z -= 980.0 * Dt;
			C->AddWorldOffset(Item.Vel * Dt);
			C->AddWorldRotation((Item.Spin * Dt).Rotation());
			if (Item.FlyTime > 3.0)
			{
				Item.FlyTime = -1.0;
				Item.Hidden = 45.0;
				C->SetVisibility(false);
			}
			continue;
		}
		if (Item.Type == 0)
		{
			C->SetWorldLocationAndRotation(Item.Home + FVector(0.0, 0.0, 10.0 * FMath::Sin(Clock * 2.5 + I)), FRotator(0.f, float(Clock * 90.0), 0.f));
		}
		for (AKapadokyaRider* R : Riders)
		{
			if (R->CrashTimer > 0.0)
			{
				continue;
			}
			double Gap = FMath::Abs(Item.S - R->TrackS);
			Gap = FMath::Min(Gap, T.Length - Gap);
			if (Gap > 95.0 || FMath::Abs(Item.Lat - R->Lateral) > (Item.Type == 0 ? 95.0 : 58.0))
			{
				continue;
			}
			if (Item.Type == 0)
			{
				if (R == Player)
				{
					TurboTime = 4.0;
					UE_LOG(LogTemp, Display, TEXT("KFUN cay alindi t=%.1f hiz %.1f"), RaceTime, R->Bike.State.Speed);
					Show(TeaJokes[JokeIndex++ % UE_ARRAY_COUNT(TeaJokes)], 2.5);
					Item.Hidden = 45.0;
					C->SetVisibility(false);
				}
				continue;
			}
			// Fici ve kasa havaya ucar
			const double H = R->Bike.State.Heading;
			const FVector Fwd(FMath::Cos(H), FMath::Sin(H), 0.0);
			Item.Vel = Fwd * (R->Bike.State.Speed * 130.0) + FVector(FMath::FRandRange(-180.0, 180.0), FMath::FRandRange(-180.0, 180.0), 620.0);
			Item.Spin = FVector(FMath::FRandRange(-400.0, 400.0), FMath::FRandRange(-400.0, 400.0), FMath::FRandRange(-400.0, 400.0));
			Item.FlyTime = 0.0;
			UE_LOG(LogTemp, Display, TEXT("KFUN %s tur %d ucuruldu t=%.1f"), R == Player ? TEXT("oyuncu") : TEXT("rakip"), Item.Type, RaceTime);
			if (R == Player && !R->bAutopilot && R->Bike.State.Speed > 6.0)
			{
				R->StartCrash(FVector(0.0, 0.0, 150.0));
			}
			else
			{
				R->Bike.State.Speed *= 0.82;
			}
			break;
		}
	}
}

void AKapadokyaRace::TickRiders(float Dt)
{
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	UpdatePack(Dt);
	UpdateFun(Dt);
	for (int32 I = 0; I < Riders.Num(); ++I)
	{
		AKapadokyaRider* R = Riders[I];
		double D = R->TrackS - PrevS[I];
		if (D < -T.Length * 0.5)
		{
			D += T.Length;
		}
		else if (D > T.Length * 0.5)
		{
			D -= T.Length;
		}
		R->TotalS += D;
		PrevS[I] = R->TrackS;
		if (!R->bFinished && R->TotalS >= RaceDistance)
		{
			Finish(R);
		}
		// Son 800 m: rakipler atak
		if (!R->bIsPlayer && RaceDistance - R->TotalS < 80000.0)
		{
			R->SetAIAggression(1.0);
		}
	}
	UpdateOrder();
	AwardPoints();
}

void AKapadokyaRace::WriteTelemetry(float Dt)
{
	if (TelemetryPath.IsEmpty() || !Player)
	{
		return;
	}
	TelemetryClock += Dt;
	if (TelemetryClock < 1.0)
	{
		return;
	}
	TelemetryClock = 0.0;
	const FBikeState& S = Player->Bike.State;
	const double Fps = Dt > 0.0 ? 1.0 / Dt : 0.0;
	UE_LOG(LogTemp, Display, TEXT("KPERF game %.1f render %.1f gpu %.1f ms frame %.1f"), FPlatformTime::ToMilliseconds(GGameThreadTime), FPlatformTime::ToMilliseconds(GRenderThreadTime), FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles()), Dt * 1000.0);
	const FString Line = FString::Printf(TEXT("%.1f,%.3f,%.0f,%.1f,%.0f,%.0f,%.0f,%.0f,%d,%.1f,%.2f,%.3f,%d,%d,%.2f,%.0f\n"),
		RaceTime, Player->TotalS / 100000.0, Player->TrackS / 100.0, S.Speed * 3.6, S.Power, S.Cadence, S.HeartRate, S.WPrime, S.Gear,
		FMath::RadiansToDegrees(S.Lean), Player->Lateral / 100.0, Player->GetGradeNow(), Player->Position, Player->CrashCount, Player->DraftFactor, Fps);
	FFileHelper::SaveStringToFile(Line, *TelemetryPath, FFileHelper::EEncodingOptions::AutoDetect, &IFileManager::Get(), FILEWRITE_Append);
}

void AKapadokyaRace::UpdateJumps()
{
	if (!JumpPoints.IsValidIndex(JumpIndex) || RaceTime < (JumpIndex + 1) * JumpEvery)
	{
		return;
	}
	// Test: tum peloton siralamasini koruyarak parkur orani JumpPoints[i] noktasina atlar
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	const double Target = JumpPoints[JumpIndex] * RaceDistance;
	double Lead = -TNumericLimits<double>::Max();
	for (const AKapadokyaRider* R : Riders)
	{
		Lead = FMath::Max(Lead, R->TotalS);
	}
	const double Speed = 10.0;
	for (int32 I = 0; I < Riders.Num(); ++I)
	{
		AKapadokyaRider* R = Riders[I];
		const double Total = Target - FMath::Min(Lead - R->TotalS, 6000.0);
		R->TeleportToS(Total + StartLineS, Total, Speed);
		PrevS[I] = R->TrackS;
	}
	UE_LOG(LogTemp, Display, TEXT("KJUMP %d oran %.2f t=%.1f"), JumpIndex, JumpPoints[JumpIndex], RaceTime);
	++JumpIndex;
}

void AKapadokyaRace::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	MenuClock += DeltaSeconds;
	if (State == EKRaceState::Menu && MenuClock > 15.0 && FParse::Param(FCommandLine::Get(), TEXT("KMenuAuto")))
	{
		UE_LOG(LogTemp, Display, TEXT("KMENU menuden yaris baslatiliyor, secili: %s"), *Menu[MenuIndex].Label);
		MenuConfirm();
	}
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	if (State == EKRaceState::Paused || State == EKRaceState::Menu)
	{
		return;
	}
	BannerTimer -= DeltaSeconds;
	ZoneTimer -= DeltaSeconds;
	if (State == EKRaceState::Countdown)
	{
		Countdown -= DeltaSeconds;
		const int32 Sec = FMath::CeilToInt(Countdown);
		if (Sec != LastBeep && Sec <= 3 && Sec > 0)
		{
			LastBeep = Sec;
			if (SndBeep)
			{
				UGameplayStatics::PlaySound2D(this, SndBeep);
			}
		}
		if (Countdown <= 0.0)
		{
			State = EKRaceState::Racing;
			if (SndGo)
			{
				UGameplayStatics::PlaySound2D(this, SndGo);
			}
			for (AKapadokyaRider* R : Riders)
			{
				R->bControlsEnabled = true;
			}
			Show(TEXT("YARIŞ BAŞLADI!"), 2.0);
		}
		return;
	}
	RaceTime += DeltaSeconds;
	UpdateJumps();
	TickRiders(DeltaSeconds);
	WriteTelemetry(DeltaSeconds);

	if (Player)
	{
		const uint8 Z = T.ZoneAt(Player->TrackS);
		if (Z != LastZone)
		{
			LastZone = Z;
			ZoneTitle = T.ZoneTitles.IsValidIndex(Z) ? T.ZoneTitles[Z] : FString();
			ZoneTimer = 4.5;
		}
		if (Crowd)
		{
			// Cars i ve zirvede seyirci sesi
			const bool bLoud = Z == 0 || T.ZoneTitles.IsValidIndex(Z) && T.ZoneTitles[Z] == TEXT("Kale Zirvesi");
			Crowd->SetVolumeMultiplier(bLoud ? 0.55f : 0.0f);
		}
	}
	if (FinishDelay > 0.0)
	{
		FinishDelay -= DeltaSeconds;
		if (FinishDelay <= 0.0)
		{
			State = EKRaceState::Results;
			if (Music)
			{
				Music->SetVolumeMultiplier(0.55f);
			}
			if (bAuto && FParse::Param(FCommandLine::Get(), TEXT("KQuit")))
			{
				FPlatformMisc::RequestExit(false, TEXT("Otomatik yaris bitti"));
			}
		}
	}
	double QuitIn = 0.0;
	if (FParse::Value(FCommandLine::Get(), TEXT("-KQuitAfter="), QuitIn) && RaceTime > QuitIn)
	{
		FPlatformMisc::RequestExit(false, TEXT("KQuitAfter"));
	}
}

AKapadokyaPC::AKapadokyaPC()
{
	bShowMouseCursor = false;
}

AKapadokyaRace* AKapadokyaPC::Race() const
{
	TActorIterator<AKapadokyaRace> It(GetWorld());
	return It ? *It : nullptr;
}

void AKapadokyaPC::SetupInputComponent()
{
	Super::SetupInputComponent();
	const auto Bind = [this](const FKey& Key, TFunction<void(AKapadokyaRace*)> Fn)
	{
		FInputKeyBinding KB(FInputChord(Key), IE_Pressed);
		KB.KeyDelegate.GetDelegateForManualSet().BindLambda([this, Fn] { if (AKapadokyaRace* R = Race()) { Fn(R); } });
		KB.bExecuteWhenPaused = true;
		KB.bConsumeInput = false;
		InputComponent->KeyBindings.Add(KB);
	};
	Bind(EKeys::Up, [](AKapadokyaRace* R) { R->MenuMove(-1); });
	Bind(EKeys::Down, [](AKapadokyaRace* R) { R->MenuMove(1); });
	Bind(EKeys::Left, [](AKapadokyaRace* R) { R->MenuChange(-1); });
	Bind(EKeys::Right, [](AKapadokyaRace* R) { R->MenuChange(1); });
	Bind(EKeys::Enter, [](AKapadokyaRace* R) { R->MenuConfirm(); });
	Bind(EKeys::Gamepad_FaceButton_Bottom, [](AKapadokyaRace* R) { R->MenuConfirm(); });
	Bind(EKeys::Gamepad_DPad_Up, [](AKapadokyaRace* R) { R->MenuMove(-1); });
	Bind(EKeys::Gamepad_DPad_Down, [](AKapadokyaRace* R) { R->MenuMove(1); });
	Bind(EKeys::Gamepad_DPad_Left, [](AKapadokyaRace* R) { R->MenuChange(-1); });
	Bind(EKeys::Gamepad_DPad_Right, [](AKapadokyaRace* R) { R->MenuChange(1); });
	Bind(EKeys::Escape, [](AKapadokyaRace* R) { R->TogglePause(); });
	Bind(EKeys::Gamepad_Special_Right, [](AKapadokyaRace* R) { R->TogglePause(); });
}
