#include "KapadokyaTrack.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

const FKapadokyaTrack& FKapadokyaTrack::Get()
{
	static FKapadokyaTrack Track;
	if (!Track.IsValid())
	{
		FString Text;
		const FString Path = FPaths::ProjectContentDir() / TEXT("Kapadokya/Data/route.json");
		TSharedPtr<FJsonObject> Root;
		if (FFileHelper::LoadFileToString(Text, *Path))
		{
			TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
			FJsonSerializer::Deserialize(Reader, Root);
		}
		if (!Root.IsValid())
		{
			UE_LOG(LogTemp, Error, TEXT("route.json okunamadi: %s"), *Path);
			return Track;
		}
		const auto& X = Root->GetArrayField(TEXT("x"));
		const auto& Y = Root->GetArrayField(TEXT("y"));
		const auto& Z = Root->GetArrayField(TEXT("z"));
		const auto& W = Root->GetArrayField(TEXT("halfwidth"));
		const auto& Sf = Root->GetArrayField(TEXT("surface"));
		const auto& Zn = Root->GetArrayField(TEXT("zone"));
		const auto& Cv = Root->GetArrayField(TEXT("curvature"));
		const int32 N = X.Num();
		Track.Points.SetNum(N);
		Track.HalfWidth.SetNum(N);
		Track.Surface.SetNum(N);
		Track.Zone.SetNum(N);
		Track.Curvature.SetNum(N);
		for (int32 I = 0; I < N; ++I)
		{
			Track.Points[I] = FVector(X[I]->AsNumber(), Y[I]->AsNumber(), Z[I]->AsNumber());
			Track.HalfWidth[I] = W[I]->AsNumber();
			Track.Surface[I] = Sf[I]->AsNumber();
			Track.Zone[I] = Zn[I]->AsNumber();
			Track.Curvature[I] = Cv[I]->AsNumber();
		}
		for (const auto& T : Root->GetArrayField(TEXT("titles")))
		{
			Track.ZoneTitles.Add(T->AsString());
		}
		Track.Length = Root->GetNumberField(TEXT("length")) * 100.0;
		Track.Step = Track.Length / N;
		Track.WaterZ = Root->GetNumberField(TEXT("water_z"));
	}
	return Track;
}

double FKapadokyaTrack::Wrap(double S) const
{
	return FMath::Fmod(FMath::Fmod(S, Length) + Length, Length);
}

int32 FKapadokyaTrack::IndexAt(double S) const
{
	return FMath::Clamp(int32(Wrap(S) / Step), 0, Points.Num() - 1);
}

FVector FKapadokyaTrack::PosAt(double S) const
{
	const double W = Wrap(S) / Step;
	const int32 A = FMath::Clamp(int32(W), 0, Points.Num() - 1);
	const int32 B = (A + 1) % Points.Num();
	return FMath::Lerp(Points[A], Points[B], W - A);
}

FVector FKapadokyaTrack::TangentAt(double S) const
{
	return (PosAt(S + Step) - PosAt(S - Step)).GetSafeNormal();
}

FVector FKapadokyaTrack::RightAt(double S) const
{
	const FVector T = TangentAt(S);
	return FVector(-T.Y, T.X, 0.0).GetSafeNormal();
}

double FKapadokyaTrack::Project(const FVector& P, double HintS, double* OutLateral) const
{
	const int32 N = Points.Num();
	int32 Best = 0;
	double BestD = TNumericLimits<double>::Max();
	const FVector2D Q(P);
	const auto Check = [&](int32 I)
	{
		const double D = FVector2D::DistSquared(Q, FVector2D(Points[I]));
		if (D < BestD)
		{
			BestD = D;
			Best = I;
		}
	};
	if (HintS < 0.0)
	{
		for (int32 I = 0; I < N; ++I)
		{
			Check(I);
		}
	}
	else
	{
		const int32 C = IndexAt(HintS);
		for (int32 O = -60; O <= 60; ++O)
		{
			Check((C + O + N) % N);
		}
	}
	const FVector A = Points[Best];
	const FVector T = TangentAt(Best * Step);
	const FVector2D Delta = Q - FVector2D(A);
	const double Along = FVector2D::DotProduct(Delta, FVector2D(T).GetSafeNormal());
	if (OutLateral)
	{
		const FVector R = RightAt(Best * Step);
		*OutLateral = FVector2D::DotProduct(Delta, FVector2D(R));
	}
	return Wrap(Best * Step + Along);
}
