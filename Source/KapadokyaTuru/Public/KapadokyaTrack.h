#pragma once
#include "CoreMinimal.h"

/** route.json'dan okunan kapali parkur. Mesafe (S) cm cinsinden. */
struct KAPADOKYATURU_API FKapadokyaTrack
{
	TArray<FVector> Points;
	TArray<float> HalfWidth;
	TArray<uint8> Surface;
	TArray<uint8> Zone;
	TArray<float> Curvature;      // 1/cm, saga +
	TArray<FString> ZoneTitles;
	double Length = 0.0;
	double Step = 200.0;
	float WaterZ = -5000.f;

	static const FKapadokyaTrack& Get();
	bool IsValid() const { return Points.Num() > 0; }

	FVector PosAt(double S) const;
	FVector TangentAt(double S) const;
	FVector RightAt(double S) const;
	int32 IndexAt(double S) const;
	float HalfWidthAt(double S) const { return HalfWidth[IndexAt(S)]; }
	float CurvatureAt(double S) const { return Curvature[IndexAt(S)]; }
	uint8 SurfaceAt(double S) const { return Surface[IndexAt(S)]; }
	uint8 ZoneAt(double S) const { return Zone[IndexAt(S)]; }
	double Wrap(double S) const;
	/** Konumu parkura izdusurur. HintS etrafinda yerel arar, HintS<0 ise tum parkur. Lateral saga +. */
	double Project(const FVector& P, double HintS, double* OutLateral = nullptr) const;
};
