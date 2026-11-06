#include "KapadokyaHUD.h"
#include "KapadokyaRace.h"
#include "KapadokyaRider.h"
#include "KapadokyaTrack.h"
#include "CanvasItem.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "EngineUtils.h"

namespace
{
	const FLinearColor Ink(0.96f, 0.93f, 0.86f);
	const FLinearColor Dim(0.72f, 0.68f, 0.60f);
	const FLinearColor Accent(0.86f, 0.13f, 0.09f);
	const FLinearColor Gold(0.95f, 0.70f, 0.22f);
	const FLinearColor Turq(0.10f, 0.62f, 0.62f);

	FString Clock(double T)
	{
		const int32 Total = FMath::Max(0, FMath::FloorToInt(T));
		const int32 Tenth = FMath::Clamp(FMath::FloorToInt((T - Total) * 10.0), 0, 9);
		return FString::Printf(TEXT("%02d:%02d.%d"), Total / 60, Total % 60, Tenth);
	}
}

AKapadokyaHUD::AKapadokyaHUD()
{
	bShowOverlays = false;
}

void AKapadokyaHUD::Text(const FString& S, float X, float Y, float Size, const FLinearColor& C, bool bCenter, bool bRight)
{
	FCanvasTextItem Item(FVector2D(X, Y), FText::FromString(S), Font, C);
	const float BaseH = Font ? Font->GetMaxCharHeight() : 20.f;
	Item.Scale = FVector2D(Size * Scale / FMath::Max(BaseH, 1.f));
	Item.EnableShadow(FLinearColor(0, 0, 0, 0.55f));
	Item.BlendMode = SE_BLEND_Translucent;
	if (bCenter)
	{
		Item.bCentreX = true;
	}
	else if (bRight)
	{
		float W, H;
		Canvas->StrLen(Font, S, W, H);
		Item.Position.X -= W * Item.Scale.X;
	}
	Canvas->DrawItem(Item);
}

void AKapadokyaHUD::Panel(float X, float Y, float W, float H, float Alpha)
{
	FCanvasTileItem Tile(FVector2D(X, Y), FVector2D(W, H), FLinearColor(0.035f, 0.03f, 0.028f, Alpha));
	Tile.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Tile);
}

void AKapadokyaHUD::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas)
	{
		return;
	}
	if (!Font)
	{
		Font = GEngine->GetLargeFont();
	}
	Scale = Canvas->ClipY / 1080.f;
	TActorIterator<AKapadokyaRace> It(GetWorld());
	AKapadokyaRace* R = It ? *It : nullptr;
	if (!R)
	{
		return;
	}
	switch (R->State)
	{
	case EKRaceState::Menu:
	case EKRaceState::Paused:
		if (R->State == EKRaceState::Paused)
		{
			DrawRace(R);
		}
		DrawMenu(R);
		break;
	case EKRaceState::Results:
		DrawResults(R);
		break;
	default:
		DrawRace(R);
		break;
	}
}

void AKapadokyaHUD::DrawRace(AKapadokyaRace* R)
{
	AKapadokyaRider* P = R->Player;
	if (!P)
	{
		return;
	}
	const FBikeState& S = P->Bike.State;
	const float W = Canvas->ClipX;
	const float H = Canvas->ClipY;

	// Sol alt: hiz ve guc
	const float Px = UI(36);
	const float Py = H - UI(240);
	Panel(Px, Py, UI(430), UI(204));
	Text(FString::Printf(TEXT("%.0f"), S.Speed * 3.6), Px + UI(28), Py + UI(6), 104, Ink);
	Text(TEXT("km/s"), Px + UI(208), Py + UI(72), 26, Dim);
	Text(FString::Printf(TEXT("%.0f W"), S.Power), Px + UI(290), Py + UI(16), 38, S.Power > P->Bike.Params.CP ? Gold : Ink);
	Text(FString::Printf(TEXT("%.0f rpm"), S.Cadence), Px + UI(290), Py + UI(60), 26, Dim);
	Text(FString::Printf(TEXT("%.0f nb"), S.HeartRate), Px + UI(290), Py + UI(92), 26, S.HeartRate > 175 ? Accent : Dim);

	// Anaerobik rezerv
	const float WFrac = float(S.WPrime / P->Bike.Params.WPrimeMax);
	Text(TEXT("Rezerv"), Px + UI(28), Py + UI(128), 22, Dim);
	Panel(Px + UI(110), Py + UI(134), UI(290), UI(14), 0.8f);
	{
		FLinearColor C = WFrac < 0.2f ? Accent : (WFrac < 0.5f ? Gold : Turq);
		C.A = 1.f;
		FCanvasTileItem Bar(FVector2D(Px + UI(110), Py + UI(134)), FVector2D(UI(290) * WFrac, UI(14)), C);
		Canvas->DrawItem(Bar);
	}
	const double Grade = P->GetGradeNow() * 100.0;
	Text(FString::Printf(TEXT("Vites %d  %s"), S.Gear + 1, FBikeDynamics::GearRatio(S.Gear) < 2.5 ? TEXT("küçük aynakol") : TEXT("büyük aynakol")), Px + UI(28), Py + UI(162), 24, Dim);
	Text(FString::Printf(TEXT("%%%+.1f"), Grade), Px + UI(320), Py + UI(158), 30, Grade > 6 ? Accent : (Grade > 3 ? Gold : Ink));

	// Ust sol: sira, tur, sure
	Panel(UI(36), UI(32), UI(330), UI(130));
	Text(FString::Printf(TEXT("%d/%d"), P->Position, R->Riders.Num()), UI(58), UI(36), 66, Gold);
	const int32 Lap = FMath::Clamp(FMath::FloorToInt(P->TotalS / FKapadokyaTrack::Get().Length) + 1, 1, R->Laps);
	Text(FString::Printf(TEXT("Tur %d/%d"), Lap, R->Laps), UI(214), UI(46), 30, Ink);
	Text(Clock(R->RaceTime), UI(214), UI(88), 30, Ink);
	const double Left = FMath::Max(0.0, (R->RaceDistance - P->TotalS) / 100000.0);
	Text(FString::Printf(TEXT("Bitişe %.1f km"), Left), UI(58), UI(118), 26, Dim);

	// Fark bilgisi: ondeki ve arkadaki
	AKapadokyaRider* Ahead = nullptr;
	AKapadokyaRider* Behind = nullptr;
	for (AKapadokyaRider* O : R->Riders)
	{
		if (O->Position == P->Position - 1)
		{
			Ahead = O;
		}
		if (O->Position == P->Position + 1)
		{
			Behind = O;
		}
	}
	float Fy = UI(176);
	const double VSafe = FMath::Max(S.Speed, 3.0) * 100.0;
	if (Ahead)
	{
		Panel(UI(36), Fy, UI(330), UI(38));
		Text(FString::Printf(TEXT("Önde %s  +%.1f sn"), *Ahead->RiderName, (Ahead->TotalS - P->TotalS) / VSafe), UI(48), Fy + UI(4), 24, Ink);
		Fy += UI(42);
	}
	if (Behind)
	{
		Panel(UI(36), Fy, UI(330), UI(38));
		Text(FString::Printf(TEXT("Arkada %s  -%.1f sn"), *Behind->RiderName, (P->TotalS - Behind->TotalS) / VSafe), UI(48), Fy + UI(4), 24, Dim);
		Fy += UI(42);
	}
	if (P->DraftFactor > 0.03)
	{
		Panel(UI(36), Fy, UI(330), UI(38));
		Text(FString::Printf(TEXT("Rüzgâr siperi  %%%.0f"), P->DraftFactor * 100.0), UI(48), Fy + UI(4), 24, Turq);
	}

	DrawMinimap(R, W - UI(290), UI(32), UI(258));
	DrawElevation(R, W - UI(530), H - UI(132), UI(494), UI(96));

	if (P->bOffRoad)
	{
		Text(TEXT("Yol dışı!"), W * 0.5f, H - UI(130), 34, Accent, true);
	}
	if (S.SlipAmount > 0.3)
	{
		Text(TEXT("Lastik kayıyor!"), W * 0.5f, H - UI(170), 34, Gold, true);
	}
	if (P->CrashTimer > 0.0)
	{
		Text(TEXT("DÜŞTÜN"), W * 0.5f, H * 0.28f, 72, Accent, true);
	}
	if (R->State == EKRaceState::Countdown)
	{
		const int32 N = FMath::CeilToInt(R->Countdown);
		Text(N <= 3 ? FString::FromInt(N) : TEXT("Hazırlan"), W * 0.5f, H * 0.28f, N <= 3 ? 150 : 72, Ink, true);
	}
	if (R->BannerTimer > 0.0)
	{
		Text(R->Banner, W * 0.5f, H * 0.18f, 50, Gold, true);
	}
	if (R->ZoneTimer > 0.0)
	{
		Text(R->ZoneTitle, W * 0.5f, UI(48), 42, Ink, true);
	}
}

void AKapadokyaHUD::DrawMinimap(AKapadokyaRace* R, float X, float Y, float Size)
{
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	if (MapPts.Num() == 0)
	{
		MapMin = FVector2D(1e12, 1e12);
		MapMax = FVector2D(-1e12, -1e12);
		for (int32 I = 0; I < T.Points.Num(); I += 8)
		{
			const FVector2D Pt(T.Points[I]);
			MapPts.Add(Pt);
			MapMin = FVector2D(FMath::Min(MapMin.X, Pt.X), FMath::Min(MapMin.Y, Pt.Y));
			MapMax = FVector2D(FMath::Max(MapMax.X, Pt.X), FMath::Max(MapMax.Y, Pt.Y));
		}
	}
	Panel(X, Y, Size, Size);
	const double Span = FMath::Max(MapMax.X - MapMin.X, MapMax.Y - MapMin.Y);
	const float Pad = UI(16);
	const float Inner = Size - 2 * Pad;
	const auto ToScreen = [&](const FVector2D& P)
	{
		// Kuzey (X+) yukari
		return FVector2D(X + Pad + (P.Y - MapMin.Y) / Span * Inner, Y + Size - Pad - (P.X - MapMin.X) / Span * Inner);
	};
	for (int32 I = 0; I < MapPts.Num(); ++I)
	{
		const FVector2D A = ToScreen(MapPts[I]);
		const FVector2D B = ToScreen(MapPts[(I + 1) % MapPts.Num()]);
		FCanvasLineItem Line(A, B);
		Line.SetColor(FLinearColor(0.9f, 0.85f, 0.75f, 0.85f));
		Line.LineThickness = UI(2.5f);
		Canvas->DrawItem(Line);
	}
	const FVector2D Start = ToScreen(FVector2D(T.PosAt(R->StartLineS)));
	FCanvasTileItem Fin(Start - FVector2D(UI(4), UI(4)), FVector2D(UI(8), UI(8)), Ink);
	Canvas->DrawItem(Fin);
	for (AKapadokyaRider* O : R->Riders)
	{
		const FVector2D Pt = ToScreen(FVector2D(O->GetActorLocation()));
		const float D = O->bIsPlayer ? UI(11) : UI(6);
		FLinearColor C = O->Color;
		C.A = 1.f;
		FCanvasTileItem Dot(Pt - FVector2D(D * 0.5f, D * 0.5f), FVector2D(D, D), O->bIsPlayer ? Gold : C * 2.5f);
		Canvas->DrawItem(Dot);
	}
}

void AKapadokyaHUD::DrawElevation(AKapadokyaRace* R, float X, float Y, float W, float H)
{
	const FKapadokyaTrack& T = FKapadokyaTrack::Get();
	Panel(X, Y, W, H);
	double ZMin = 1e12, ZMax = -1e12;
	for (int32 I = 0; I < T.Points.Num(); I += 20)
	{
		ZMin = FMath::Min(ZMin, T.Points[I].Z);
		ZMax = FMath::Max(ZMax, T.Points[I].Z);
	}
	const float Pad = UI(10);
	const int32 Steps = 96;
	const auto Point = [&](double U)
	{
		const double S = R->StartLineS + U * T.Length;
		const double Z = (T.PosAt(S).Z - ZMin) / FMath::Max(ZMax - ZMin, 1.0);
		return FVector2D(X + Pad + U * (W - 2 * Pad), Y + H - Pad - Z * (H - 2 * Pad));
	};
	for (int32 I = 0; I < Steps; ++I)
	{
		FCanvasLineItem Line(Point(double(I) / Steps), Point(double(I + 1) / Steps));
		Line.SetColor(FLinearColor(0.85f, 0.65f, 0.45f, 0.95f));
		Line.LineThickness = UI(2.f);
		Canvas->DrawItem(Line);
	}
	if (R->Player)
	{
		const double U = T.Wrap(R->Player->TrackS - R->StartLineS) / T.Length;
		const FVector2D Pt = Point(U);
		FCanvasTileItem Dot(Pt - FVector2D(UI(5), UI(5)), FVector2D(UI(10), UI(10)), Gold);
		Canvas->DrawItem(Dot);
	}
}

void AKapadokyaHUD::DrawMenu(AKapadokyaRace* R)
{
	const float W = Canvas->ClipX;
	const float H = Canvas->ClipY;
	Panel(0, 0, W, H, R->State == EKRaceState::Paused ? 0.45f : 0.12f);
	// Parlak gokyuzunde de okunsun: menu kolonu arkasinda koyu panel
	Panel(UI(70), UI(90), UI(960), UI(960), 0.55f);
	const float X = UI(110);
	float Y = UI(120);
	if (R->State == EKRaceState::Menu)
	{
		Text(TEXT("KAPADOKYA TURU"), X, Y, 96, Ink);
		Y += UI(112);
		Text(TEXT("Peribacaları arasında 7,5 km'lik yarış"), X, Y, 32, Gold);
		Y += UI(80);
	}
	else
	{
		Text(TEXT("Mola"), X, Y, 72, Ink);
		Y += UI(110);
	}
	for (int32 I = 0; I < R->Menu.Num(); ++I)
	{
		const FKMenuItem& Item = R->Menu[I];
		const bool bSel = I == R->MenuIndex;
		if (bSel)
		{
			FCanvasTileItem Tile(FVector2D(X - UI(16), Y), FVector2D(UI(620), UI(54)), FLinearColor(Accent.R, Accent.G, Accent.B, 0.82f));
			Tile.BlendMode = SE_BLEND_Translucent;
			Canvas->DrawItem(Tile);
		}
		Text(Item.Label, X, Y + UI(8), 36, bSel ? FLinearColor::White : Ink);
		if (Item.Options.Num() > 0)
		{
			Text(FString::Printf(TEXT("< %s >"), *Item.Options[Item.Value]), X + UI(240), Y + UI(8), 36, bSel ? FLinearColor::White : Dim);
		}
		Y += UI(62);
	}
	Y = H - UI(238);
	Panel(X - UI(16), Y - UI(12), UI(760), UI(222));
	const TCHAR* Help[] = {
		TEXT("W / sağ tetik: pedal      S / sol tetik: fren"),
		TEXT("A D / sol çubuk: yatış ve direksiyon"),
		TEXT("Shift: sprint (rezervi tüketir)      Boşluk: aero pozisyon"),
		TEXT("Q E: elle vites      R: otomatik vites      C: kamera"),
		TEXT("Esc: mola      Oklar + Enter: menü"),
	};
	for (const TCHAR* Line : Help)
	{
		Text(Line, X, Y, 26, Ink);
		Y += UI(38);
	}
	Text(TEXT("Powered by Poly Haven (CC0 dokular)"), W - UI(36), H - UI(50), 22, Dim, false, true);
}

void AKapadokyaHUD::DrawResults(AKapadokyaRace* R)
{
	const float W = Canvas->ClipX;
	Panel(0, 0, W, Canvas->ClipY, 0.55f);
	float Y = UI(70);
	const float X = UI(260);
	Text(TEXT("SONUÇLAR"), X, Y, 72, Ink);
	Y += UI(92);
	TArray<AKapadokyaRider*> Order;
	for (AKapadokyaRider* Rr : R->Riders)
	{
		Order.Add(Rr);
	}
	Order.Sort([](const AKapadokyaRider& A, const AKapadokyaRider& B) { return A.Position < B.Position; });
	Text(TEXT("Sıra"), X, Y, 26, Dim);
	Text(TEXT("Sporcu"), X + UI(90), Y, 26, Dim);
	Text(TEXT("Takım"), X + UI(420), Y, 26, Dim);
	Text(TEXT("Süre"), X + UI(760), Y, 26, Dim);
	Text(TEXT("Zirve"), X + UI(960), Y, 26, Dim);
	Text(TEXT("Sprint"), X + UI(1080), Y, 26, Dim);
	Y += UI(44);
	const double Winner = Order.Num() > 0 && Order[0]->bFinished ? Order[0]->FinishTime : 0.0;
	for (AKapadokyaRider* O : Order)
	{
		const FLinearColor C = O->bIsPlayer ? Gold : Ink;
		Text(FString::FromInt(O->Position), X, Y, 32, C);
		Text(O->RiderName, X + UI(90), Y, 32, C);
		Text(O->TeamName, X + UI(420), Y, 32, O->bIsPlayer ? Gold : Dim);
		FString Time;
		if (O->bFinished)
		{
			Time = O->Position == 1 ? Clock(O->FinishTime) : FString::Printf(TEXT("+%s"), *Clock(O->FinishTime - Winner));
		}
		else
		{
			Time = TEXT("yolda");
		}
		Text(Time, X + UI(760), Y, 32, C);
		Text(FString::FromInt(O->KomPoints % 1000), X + UI(960), Y, 32, C);
		Text(FString::FromInt(O->SprintPoints % 1000), X + UI(1080), Y, 32, C);
		Y += UI(46);
	}
	Y += UI(24);
	Text(TEXT("Enter: yeniden yarış"), X, Y, 32, Gold);
}
