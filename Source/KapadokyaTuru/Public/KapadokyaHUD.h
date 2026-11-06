#pragma once
#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "KapadokyaHUD.generated.h"

class AKapadokyaRace;
class UFont;

UCLASS()
class KAPADOKYATURU_API AKapadokyaHUD : public AHUD
{
	GENERATED_BODY()
public:
	AKapadokyaHUD();
	virtual void DrawHUD() override;

private:
	void DrawRace(AKapadokyaRace* R);
	void DrawMenu(AKapadokyaRace* R);
	void DrawResults(AKapadokyaRace* R);
	void DrawMinimap(AKapadokyaRace* R, float X, float Y, float Size);
	void DrawElevation(AKapadokyaRace* R, float X, float Y, float W, float H);
	void Text(const FString& S, float X, float Y, float Size, const FLinearColor& C, bool bCenter = false, bool bRight = false);
	void Panel(float X, float Y, float W, float H, float Alpha = 0.55f);
	float UI(float V) const { return V * Scale; }

	UPROPERTY() TObjectPtr<UFont> Font;
	float Scale = 1.f;
	TArray<FVector2D> MapPts;
	FVector2D MapMin, MapMax;
};
