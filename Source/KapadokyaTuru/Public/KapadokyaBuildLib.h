#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "KapadokyaBuildLib.generated.h"

/** Tools/ altindaki uretecilerin ciktilarini editorde StaticMesh varligina donusturur. */
UCLASS()
class KAPADOKYATURU_API UKapadokyaBuildLib : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/**
	 * Bir .kmsh dosyasindan StaticMesh uretip kaydeder.
	 * @param CollisionMode 0 yok, 1 karmasik (trimesh), 2 basit kutu
	 */
	UFUNCTION(BlueprintCallable, Category = "Kapadokya")
	static bool BuildMeshFromFile(const FString& FilePath, const FString& AssetPath, const TArray<FString>& MaterialPaths,
		bool bNanite, int32 CollisionMode, bool bDistanceField);

	/**
	 * MetaHuman govde + kiyafet + yuz'u verilen pozda tek .kmsh dosyasina pisirir (seyirci icin).
	 * Yuvalar: 0 govde, 1 gomlek, 2 sort, 3 yuz, 4 dis, 5 sol goz, 6 sag goz, 7 sac. Kirpik/kabuk atlanir.
	 * HairPath: bos olabilir; sac karti StaticMesh'i, bas hareket etmedigi icin aynen eklenir.
	 * @param PoseId 0 ayakta, 1 iki kol yukari, 2 tek kol yukari, 3 eller onde
	 */
	UFUNCTION(BlueprintCallable, Category = "Kapadokya")
	static bool BakeHumanPose(const FString& BodyPath, const FString& OutfitPath, const FString& FacePath, const FString& HairPath, int32 Lod, int32 PoseId, const FString& OutFile);
};
