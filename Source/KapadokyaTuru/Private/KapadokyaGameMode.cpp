#include "KapadokyaGameMode.h"
#include "KapadokyaHUD.h"
#include "KapadokyaRace.h"
#include "KapadokyaRider.h"
#include "KapadokyaTrack.h"
#include "KapadokyaWorld.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpectatorPawn.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Kismet/KismetRenderingLibrary.h"

AKapadokyaGameMode::AKapadokyaGameMode()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bTickEvenWhenPaused = true;
	DefaultPawnClass = ASpectatorPawn::StaticClass();
	PlayerControllerClass = AKapadokyaPC::StaticClass();
	HUDClass = AKapadokyaHUD::StaticClass();
}

void AKapadokyaGameMode::BeginPlay()
{
	Super::BeginPlay();
	World = GetWorld()->SpawnActor<AKapadokyaWorld>();
	// M2 olcumu: Dusuk ~26 fps, Orta ~18 fps. Varsayilan oynanabilir olan; menuden yukseltilebilir.
	int32 Q = 0;
	FParse::Value(FCommandLine::Get(), TEXT("-KQuality="), Q);
	World->ApplyQuality(Q);
	// Test: kalite ayarindan sonra uygulanan ayarlar. -KCVars=r.Nanite=0;r.Lumen.X=1
	FString ExtraCVars;
	if (FParse::Value(FCommandLine::Get(), TEXT("-KCVars="), ExtraCVars, false))
	{
		TArray<FString> Parts;
		ExtraCVars.ParseIntoArray(Parts, TEXT(";"));
		for (FString Part : Parts)
		{
			// Dogrudan degisken: Shipping'de konsol komutu calismaz
			FString CvarName, CvarValue;
			if (Part.Split(TEXT("="), &CvarName, &CvarValue))
			{
				if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(*CvarName))
				{
					Var->Set(*CvarValue, ECVF_SetByCode);
				}
			}
		}
	}
	FParse::Value(FCommandLine::Get(), TEXT("-KProfileAt="), ProfileAt);
	FParse::Value(FCommandLine::Get(), TEXT("-KCsvAt="), CsvAt);
	bHitchLog = FParse::Param(FCommandLine::Get(), TEXT("KHitch"));
	int32 Tod = 0;
	FParse::Value(FCommandLine::Get(), TEXT("-KTime="), Tod);
	World->ApplyTimeOfDay(EKTimeOfDay(FMath::Clamp(Tod, 0, 2)));

	// Normal oyun: yaris. -KShots modunda sadece dunya gorunur.
	if (!FParse::Param(FCommandLine::Get(), TEXT("KNoRace")))
	{
		Race = GetWorld()->SpawnActor<AKapadokyaRace>();
		Race->Setup(World);
		FString RaceShots;
		if (FParse::Value(FCommandLine::Get(), TEXT("-KRaceShots="), RaceShots, false))
		{
			TArray<FString> Parts;
			RaceShots.ParseIntoArray(Parts, TEXT(","));
			for (const FString& Part : Parts)
			{
				RaceShotTimes.Add(FCString::Atod(*Part));
			}
			FParse::Value(FCommandLine::Get(), TEXT("-KShotTag="), ShotTag);
		}
	}

	// Test araci: -KShots=0.02,0.2,... rota orani noktalarindan otomatik ekran goruntusu
	FString Shots;
	if (FParse::Value(FCommandLine::Get(), TEXT("-KShots="), Shots, false))
	{
		TArray<FString> Parts;
		Shots.ParseIntoArray(Parts, TEXT(","));
		for (const FString& Part : Parts)
		{
			ShotList.Add(FCString::Atod(*Part));
		}
		FParse::Value(FCommandLine::Get(), TEXT("-KShotTag="), ShotTag);
		ShotIndex = 0;
		ShotTimer = 12.0; // ilk karede shader ve Lumen oturmasi icin bekle
	}
}

void AKapadokyaGameMode::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (Race && RaceShotTimes.IsValidIndex(RaceShotIndex) && Race->RaceTime >= RaceShotTimes[RaceShotIndex])
	{
		const FString Dir = FPaths::ProjectSavedDir() / TEXT("KShots");
		IFileManager::Get().MakeDirectory(*Dir, true);
		const FString File = Dir / FString::Printf(TEXT("%s_r%02d.png"), *ShotTag, RaceShotIndex);
		// Pencere arkadayken de calissin: sahneyi dogrudan ayri hedefe ciz
		if (APlayerController* ShotPC = GetWorld()->GetFirstPlayerController())
		{
			if (ShotPC->PlayerCameraManager)
			{
				UTextureRenderTarget2D* Target = UKismetRenderingLibrary::CreateRenderTarget2D(this, 1280, 720, RTF_RGBA8_SRGB);
				USceneCaptureComponent2D* Capture = NewObject<USceneCaptureComponent2D>(this);
				Capture->bCaptureEveryFrame = false;
				Capture->bCaptureOnMovement = false;
				Capture->CaptureSource = SCS_FinalColorLDR;
				Capture->TextureTarget = Target;
				Capture->FOVAngle = ShotPC->PlayerCameraManager->GetFOVAngle();
				Capture->RegisterComponent();
				Capture->SetWorldLocationAndRotation(ShotPC->PlayerCameraManager->GetCameraLocation(), ShotPC->PlayerCameraManager->GetCameraRotation());
				// Test: oyuncuya yandan ve onden yakin cekim (eller, ayaklar, tekerlek-yol temasi)
				if (FParse::Param(FCommandLine::Get(), TEXT("KCloseShots")) && Race->Player)
				{
					const FVector At = Race->Player->GetActorLocation();
					const FRotator Bike = Race->Player->GetActorRotation();
					const double H = Race->Player->Bike.State.Heading;
					const FVector Fwd(FMath::Cos(H), FMath::Sin(H), 0.0);
					const FVector Right(-Fwd.Y, Fwd.X, 0.0);
					const FVector Offs[] = { Right * 260.0 + FVector(0, 0, 90), Fwd * 110.0 + Right * 95.0 + FVector(0, 0, 105), Right * 120.0 + FVector(0, 0, 14), Fwd * 45.0 + Right * 55.0 + FVector(0, 0, 125) };
					const FVector Looks[] = { At + FVector(0, 0, 80), At + Fwd * 40.0 + FVector(0, 0, 95), At + FVector(0, 0, 18), At + Fwd * 45.0 + FVector(0, 0, 95) };
					const int32 V = RaceShotIndex % 4;
					Capture->FOVAngle = 55.f;
					Capture->SetWorldLocationAndRotation(At + Offs[V], (Looks[V] - (At + Offs[V])).Rotation());
				}
				Capture->CaptureScene();
				UKismetRenderingLibrary::ExportRenderTarget(this, Target, Dir, FPaths::GetCleanFilename(File));
				Capture->DestroyComponent();
			}
		}
		UE_LOG(LogTemp, Display, TEXT("KRACESHOT %d t=%.1f dosya %s"), RaceShotIndex, Race->RaceTime, *File);
		++RaceShotIndex;
	}
	// Test: kubbe yonunu bulmak icin dort yone kare
	if (FParse::Param(FCommandLine::Get(), TEXT("KSkyProbe")) && World && SkyProbeIndex < 4)
	{
		SkyProbeTimer += DeltaSeconds;
		if (SkyProbeTimer > 8.0)
		{
			UTextureRenderTarget2D* Target = UKismetRenderingLibrary::CreateRenderTarget2D(this, 960, 960, RTF_RGBA8_SRGB);
			USceneCaptureComponent2D* Capture = NewObject<USceneCaptureComponent2D>(this);
			Capture->bCaptureEveryFrame = false;
			Capture->bCaptureOnMovement = false;
			Capture->CaptureSource = SCS_FinalColorLDR;
			Capture->TextureTarget = Target;
			Capture->FOVAngle = 90.f;
			Capture->RegisterComponent();
			Capture->SetWorldLocationAndRotation(FVector(0, 0, 30000), FRotator(35.0, SkyProbeIndex * 90.0, 0.0));
			Capture->CaptureScene();
			UKismetRenderingLibrary::ExportRenderTarget(this, Target, FPaths::ProjectSavedDir() / TEXT("KShots"), FString::Printf(TEXT("probe_%d.png"), SkyProbeIndex));
			Capture->DestroyComponent();
			if (++SkyProbeIndex == 4)
			{
				FPlatformMisc::RequestExit(false, TEXT("KSkyProbe"));
			}
			SkyProbeTimer = 7.0;
		}
	}
	// Test: oyuncuyu zorla dusur. -KCrashAt=saniye
	{
		static double CrashAt = -2.0;
		if (CrashAt < -1.0)
		{
			CrashAt = -1.0;
			FParse::Value(FCommandLine::Get(), TEXT("-KCrashAt="), CrashAt);
		}
		if (Race && Race->Player && CrashAt > 0.0 && Race->RaceTime >= CrashAt)
		{
			CrashAt = -1.0;
			Race->Player->StartCrash(FVector(0.0, 120.0, 60.0));
		}
	}
	// Test: kare kare dagilim (15 sn pencere). Isinlanma sonrasi ilk 2 sn sayilmaz.
	if (bHitchLog && Race && Race->RaceTime > 0.0)
	{
		const double Dt = FApp::GetDeltaTime() * 1000.0;
		if (Dt > 300.0 || HitchIgnore > 0.0)
		{
			HitchIgnore = Dt > 300.0 ? 2.0 : HitchIgnore - DeltaSeconds;
		}
		else
		{
			HitchFrames.Add(float(Dt));
		}
		HitchClock += DeltaSeconds;
		if (HitchClock >= 12.0 && HitchFrames.Num() > 10)
		{
			HitchFrames.Sort();
			const int32 N = HitchFrames.Num();
			int32 Over50 = 0, Over100 = 0;
			for (float F : HitchFrames) { Over50 += F > 50.f; Over100 += F > 100.f; }
			const FString HitchLine = FString::Printf(TEXT("KHITCH n %d p50 %.1f p95 %.1f p99 %.1f max %.1f over50 %d over100 %d\n"), N, HitchFrames[N / 2], HitchFrames[N * 95 / 100], HitchFrames[N * 99 / 100], HitchFrames[N - 1], Over50, Over100);
			UE_LOG(LogTemp, Display, TEXT("%s"), *HitchLine);
			// Shipping derlemede log yok: dosyaya da yaz
			FFileHelper::SaveStringToFile(HitchLine, *(FPaths::ProjectSavedDir() / TEXT("khitch.txt")), FFileHelper::EEncodingOptions::AutoDetect, &IFileManager::Get(), FILEWRITE_Append);
			HitchFrames.Reset();
			HitchClock = 0.0;
		}
	}
	if (Race && CsvAt > 0.0 && Race->RaceTime >= CsvAt)
	{
		CsvAt = -1.0;
		GEngine->Exec(GetWorld(), TEXT("CsvProfile Frames=250"));
	}
	if (Race && ProfileAt > 0.0 && Race->RaceTime >= ProfileAt)
	{
		ProfileAt = -1.0;
		GEngine->Exec(GetWorld(), TEXT("ProfileGPU"));
	}
	// Test: oyundaki gercek goruntu (HUD ve dinamik cozunurluk dahil). -KViewShots=20,40
	{
		static TArray<double> ViewShots;
		static int32 ViewShotIndex = -1;
		if (ViewShotIndex < 0)
		{
			ViewShotIndex = 0;
			FString Spec;
			if (FParse::Value(FCommandLine::Get(), TEXT("-KViewShots="), Spec, false))
			{
				TArray<FString> Parts;
				Spec.ParseIntoArray(Parts, TEXT(","));
				for (const FString& Part : Parts)
				{
					ViewShots.Add(FCString::Atod(*Part));
				}
			}
		}
		if (ViewShots.IsValidIndex(ViewShotIndex) && GetWorld()->GetRealTimeSeconds() >= ViewShots[ViewShotIndex])
		{
			const FString ViewFile = FPaths::ProjectSavedDir() / FString::Printf(TEXT("KShots/view_%02d.png"), ViewShotIndex);
			FScreenshotRequest::RequestScreenshot(ViewFile, true, false);
			++ViewShotIndex;
		}
	}
	// Test: menu ekrani HUD ile (pencere onde olmali)
	if (Race && !bMenuShotDone && Race->State == EKRaceState::Menu && Race->MenuClock > 11.0 && FParse::Param(FCommandLine::Get(), TEXT("KMenuAuto")))
	{
		bMenuShotDone = true;
		FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / TEXT("KShots/menu.png"), true, false);
	}
	if (ShotIndex < 0)
	{
		return;
	}
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	const FKapadokyaTrack& Track = FKapadokyaTrack::Get();
	if (!PC || !Track.IsValid())
	{
		return;
	}
	if (ShotIndex >= ShotList.Num())
	{
		FPlatformMisc::RequestExit(false, TEXT("KShots bitti"));
		ShotIndex = -1;
		return;
	}
	const double S = ShotList[ShotIndex] * Track.Length;
	const FVector Pos = Track.PosAt(S) + FVector(0, 0, 170.0);
	const FVector Ahead = Track.PosAt(S + 2500.0) + FVector(0, 0, 120.0);
	const FRotator Rot = (Ahead - Pos).Rotation();
	if (APawn* Pawn = PC->GetPawn())
	{
		Pawn->SetActorLocation(Pos);
	}
	PC->SetControlRotation(Rot);
	FpsSum += DeltaSeconds;
	++FpsFrames;
	ShotTimer -= DeltaSeconds;
	if (ShotTimer <= 0.0)
	{
		const FString Dir = FPaths::ProjectSavedDir() / TEXT("KShots");
		IFileManager::Get().MakeDirectory(*Dir, true);
		const FString File = Dir / FString::Printf(TEXT("%s_%02d.png"), *ShotTag, ShotIndex);
		FScreenshotRequest::RequestScreenshot(File, false, false);
		const double AvgMs = 1000.0 * FpsSum / FMath::Max(FpsFrames, 1);
		UE_LOG(LogTemp, Display, TEXT("KSHOT %d S=%.3f ort kare %.1f ms (%.1f fps) dosya %s"), ShotIndex, ShotList[ShotIndex], AvgMs, 1000.0 / AvgMs, *File);
		++ShotIndex;
		ShotTimer = 4.0;
		FpsSum = 0.0;
		FpsFrames = 0;
	}
}
