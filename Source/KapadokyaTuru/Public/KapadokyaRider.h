#pragma once
#include "CoreMinimal.h"
#include "BikeDynamics.h"
#include "GameFramework/Pawn.h"
#include "KapadokyaRider.generated.h"

class UAudioComponent;
class UCameraComponent;
class UMaterialInstanceDynamic;
class UPoseableMeshComponent;
class USkeletalMeshComponent;
class USoundBase;
class UStaticMeshComponent;

UENUM()
enum class EKCameraMode : uint8 { Chase, Near, Bars, Broadcast, Count };

/** Bisiklet + sporcu. Oyuncu ve yapay zeka ayni fizik modelini kullanir. */
UCLASS()
class KAPADOKYATURU_API AKapadokyaRider : public APawn
{
	GENERATED_BODY()
public:
	AKapadokyaRider();

	void InitRider(int32 InId, const FString& InName, const FString& InTeam, const FLinearColor& TeamColor, const FLinearColor& TeamColor2, bool bInPlayer, double StartS, double StartLat, double Strength);

	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* Input) override;

	// --- Yaris arayuzu ---
	FBikeDynamics Bike;
	FString RiderName;
	FString TeamName;
	FLinearColor Color = FLinearColor::Red;
	int32 Id = 0;
	bool bIsPlayer = false;
	/** Golge mesafesi (metre): altinda tam, 2 kati altinda sadece govde. Kalite ayarindan gelir. */
	static double ShadowNearM;
	bool bAutopilot = false;
	bool bKeyboardBot = false;
	bool bAssist = true;
	bool bControlsEnabled = false;
	bool bFinished = false;
	double FinishTime = 0.0;

	double TrackS = 0.0;          // cm, tur icinde
	double TotalS = 0.0;          // cm, baslangictan beri
	double Lateral = 0.0;         // cm
	double DraftFactor = 0.0;
	double PushLateral = 0.0;     // cm/s, yanindaki sporculardan kacinma
	int32 Position = 1;
	int32 KomPoints = 0;
	int32 SprintPoints = 0;
	bool bRespawning = false;
	bool bOffRoad = false;
	double CrashTimer = 0.0;
	/** Oncedeki kaza: kalan mesafe (cm, <0 yok) ve yanal konum. Yaris her kare yeniler. */
	double HazardDist = -1.0;
	double HazardLat = 0.0;
	int32 CrashCount = 0;
	uint8 CurrentSurface = 0;

	void StartCrash(const FVector& Impulse);
	void AddAssistNudge(double Cm) { AssistLane += Cm; }
	/** Eglence modu: sporcu ve bisiklet havaya firlar. */
	void FunLaunch();
	/** Test araci: sporcuyu parkurda verilen noktaya tasir. */
	void TeleportToS(double NewS, double NewTotalS, double SpeedMs);
	void CycleCamera();
	EKCameraMode GetCameraMode() const { return CameraMode; }
	void SetAIAggression(double Value) { AIAggression = Value; }
	void SetLaneTarget(double Value) { AILane = Value; }
	double GetGradeNow() const { return GradeNow; }

	/** Oyuncu girdileri: dokunmatik/menu olmayan yol. */
	void OnThrottle(float V) { InThrottle = V; }
	void OnBrake(float V) { InBrake = V; }
	void OnSteer(float V) { InSteer = V; }

private:
	void BuildVisual();
	void InitPose();
	void UpdatePose(float Dt);
	void UpdateShadowLod(float Dt);
	void ApplyTeamToJersey();
	int32 ForcedLod = -1;
	FLinearColor JerseyA = FLinearColor::Red;
	FLinearColor JerseyB = FLinearColor::White;
	int32 ShadowLevel = -1;
	float ShadowClock = 0.f;
	void UpdateMotion(float Dt);
	void UpdatePlayerInput(float Dt, FBikeInput& Out);
	void UpdateAI(float Dt, FBikeInput& Out);
	double SafeSpeedAhead() const;
	double LaneFollowAccel(double LaneCm) const;
	void UpdateCamera(float Dt);
	void UpdateAudio(float Dt);
	void Respawn();

	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<USceneComponent> LeanRoot;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> FrameMesh;
	UPROPERTY() TObjectPtr<USceneComponent> SteerPivot;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> SteerMesh;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> FrontWheel;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> RearWheel;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> CrankMesh;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> PedalR;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> PedalL;
	UPROPERTY() TObjectPtr<UPoseableMeshComponent> Body;
	UPROPERTY() TObjectPtr<USkeletalMeshComponent> Face;
	UPROPERTY() TObjectPtr<USkeletalMeshComponent> Outfit;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> JerseyMID;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Helmet;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Glasses;
	UPROPERTY() TObjectPtr<USkeletalMeshComponent> Ragdoll;
	UPROPERTY() TObjectPtr<class UBoxComponent> CrashBody;
	UPROPERTY() TArray<TObjectPtr<class UBoxComponent>> CrashFloor;
	void EndCrashPhysics();
	UPROPERTY() TObjectPtr<UCameraComponent> Camera;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> PaintMID;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BodyMID;

	UPROPERTY() TObjectPtr<UAudioComponent> SndTyre;
	UPROPERTY() TObjectPtr<UAudioComponent> SndWind;
	UPROPERTY() TObjectPtr<UAudioComponent> SndFreewheel;
	UPROPERTY() TObjectPtr<UAudioComponent> SndChain;
	UPROPERTY() TObjectPtr<UAudioComponent> SndCobble;
	UPROPERTY() TObjectPtr<UAudioComponent> SndBreath;
	UPROPERTY() TObjectPtr<USoundBase> SndShift;
	UPROPERTY() TObjectPtr<USoundBase> SndCrash;

	// Kemik onbellegi
	struct FBoneIds
	{
		int32 Pelvis = -1, Spine[5] = { -1,-1,-1,-1,-1 }, Neck = -1, Head = -1;
		int32 ClavicleL = -1, UpperArmL = -1, LowerArmL = -1, HandL = -1;
		int32 ClavicleR = -1, UpperArmR = -1, LowerArmR = -1, HandR = -1;
		int32 ThighL = -1, CalfL = -1, FootL = -1, BallL = -1;
		int32 ThighR = -1, CalfR = -1, FootR = -1, BallR = -1;
	} Bones;
	TArray<FTransform> RefCS;
	TArray<FTransform> RefLocal;
	TArray<int32> Parent;
	TArray<FTransform> PoseCS;
	TArray<int32> FingerBones;
	bool bPoseReady = false;
	double RightSideSign = 1.0;  // sag kemiklerin mesh X isareti
	int32 PoseFrameSkip = 0;

	// Giris
	float InThrottle = 0.f;
	float InBrake = 0.f;
	float InSteer = 0.f;
	bool bInSprint = false;
	bool bInTuck = false;
	bool bManualGears = false;
	int32 PendingGear = 0;
	double SmoothSteer = 0.0;
	double SmoothThrottle = 0.0;
	double AssistLane = 0.0;

	// YZ
	double AIAggression = 0.5;
	double AILane = 0.0;
	double AIStrength = 1.0;
	double AISeed = 0.0;
	double AIEffortNow = 0.8;

	// Hareket
	FVector Pos = FVector::ZeroVector;
	double GroundZ = 0.0;
	double VerticalSpeed = 0.0;
	double PitchRad = 0.0;
	double GradeNow = 0.0;
	double ShakeEnergy = 0.0;
	double StandAlpha = 0.0;
	double BrakeDive = 0.0;
	double AeroAlpha = 0.0;
	double LastSteerVisual = 0.0;
	FVector CrashBikeVel = FVector::ZeroVector;
	FVector CrashAngVel = FVector::ZeroVector;

	// Kamera
	EKCameraMode CameraMode = EKCameraMode::Chase;
	FVector CamPos = FVector::ZeroVector;
	FVector BroadcastAnchor = FVector::ZeroVector;
	double CamYaw = 0.0;
	double CamRoll = 0.0;
	double CamFov = 75.0;
	double ShakeT = 0.0;
	bool bCamInit = false;
	int32 LastGear = -1;
};
