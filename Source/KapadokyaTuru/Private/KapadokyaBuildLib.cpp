#include "KapadokyaBuildLib.h"

#if WITH_EDITOR
#include "AssetRegistry/AssetRegistryModule.h"
#include "DistanceFieldAtlas.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Engine/SkeletalMesh.h"
#include "MeshDescription.h"
#include "ReferenceSkeleton.h"
#include "SkeletalMeshAttributes.h"
#include "Misc/FileHelper.h"
#include "PhysicsEngine/BodySetup.h"
#include "StaticMeshAttributes.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"

namespace
{
	template <typename T>
	const T* TakeSpan(const uint8*& Cursor, int64 Count)
	{
		const T* Result = reinterpret_cast<const T*>(Cursor);
		Cursor += Count * sizeof(T);
		return Result;
	}
}
#endif

bool UKapadokyaBuildLib::BuildMeshFromFile(const FString& FilePath, const FString& AssetPath, const TArray<FString>& MaterialPaths,
	bool bNanite, int32 CollisionMode, bool bDistanceField)
{
#if WITH_EDITOR
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *FilePath) || Bytes.Num() < 12 || FMemory::Memcmp(Bytes.GetData(), "KMS1", 4) != 0)
	{
		UE_LOG(LogTemp, Error, TEXT("KMSH okunamadi: %s"), *FilePath);
		return false;
	}
	const uint8* Cursor = Bytes.GetData() + 4;
	const uint32 NumVerts = *TakeSpan<uint32>(Cursor, 1);
	const uint32 NumTris = *TakeSpan<uint32>(Cursor, 1);
	const int64 Expected = 12 + int64(NumVerts) * (12 + 12 + 8 + 8 + 4) + int64(NumTris) * (12 + 1);
	if (Bytes.Num() != Expected)
	{
		UE_LOG(LogTemp, Error, TEXT("KMSH boyutu hatali: %s (%d, beklenen %lld)"), *FilePath, Bytes.Num(), Expected);
		return false;
	}
	const FVector3f* Pos = TakeSpan<FVector3f>(Cursor, NumVerts);
	const FVector3f* Nor = TakeSpan<FVector3f>(Cursor, NumVerts);
	const FVector2f* Uv0 = TakeSpan<FVector2f>(Cursor, NumVerts);
	const FVector2f* Uv1 = TakeSpan<FVector2f>(Cursor, NumVerts);
	const FColor* Rgba = reinterpret_cast<const FColor*>(TakeSpan<uint32>(Cursor, NumVerts));
	const uint32* Idx = TakeSpan<uint32>(Cursor, int64(NumTris) * 3);
	const uint8* Mat = TakeSpan<uint8>(Cursor, NumTris);

	const FString Name = FPackageName::GetLongPackageAssetName(AssetPath);
	UPackage* Package = CreatePackage(*AssetPath);
	Package->FullyLoad();
	UStaticMesh* Mesh = FindObject<UStaticMesh>(Package, *Name);
	// Onceki varliklarin arka plan DF/kart isleri bitmeden kaynak modeli silmek motoru dusuruyor
	if (GDistanceFieldAsyncQueue)
	{
		GDistanceFieldAsyncQueue->BlockUntilAllBuildsComplete();
	}
	if (Mesh)
	{
		Mesh->SetNumSourceModels(0);
		Mesh->GetStaticMaterials().Empty();
	}
	else
	{
		Mesh = NewObject<UStaticMesh>(Package, *Name, RF_Public | RF_Standalone);
	}

	FMeshDescription Desc;
	FStaticMeshAttributes Attr(Desc);
	Attr.Register();
	auto VertexPos = Attr.GetVertexPositions();
	auto InstNormal = Attr.GetVertexInstanceNormals();
	auto InstUV = Attr.GetVertexInstanceUVs();
	auto InstColor = Attr.GetVertexInstanceColors();
	auto GroupSlot = Attr.GetPolygonGroupMaterialSlotNames();
	InstUV.SetNumChannels(2);

	Desc.ReserveNewVertices(NumVerts);
	Desc.ReserveNewVertexInstances(NumVerts);
	Desc.ReserveNewTriangles(NumTris);

	TArray<FVertexInstanceID> Instances;
	Instances.SetNumUninitialized(NumVerts);
	for (uint32 V = 0; V < NumVerts; ++V)
	{
		const FVertexID Vid = Desc.CreateVertex();
		VertexPos[Vid] = Pos[V];
		const FVertexInstanceID Iid = Desc.CreateVertexInstance(Vid);
		InstNormal[Iid] = Nor[V];
		InstUV.Set(Iid, 0, Uv0[V]);
		InstUV.Set(Iid, 1, Uv1[V]);
		// Dosyada RGBA sirasi; FColor bellekte BGRA'dir
		const FColor& Raw = Rgba[V];
		InstColor[Iid] = FVector4f(Raw.B / 255.f, Raw.G / 255.f, Raw.R / 255.f, Raw.A / 255.f);
		Instances[V] = Iid;
	}

	const int32 NumSlots = FMath::Max(1, MaterialPaths.Num());
	TArray<FPolygonGroupID> Groups;
	for (int32 S = 0; S < NumSlots; ++S)
	{
		const FName Slot(*FString::Printf(TEXT("M%d"), S));
		const FPolygonGroupID G = Desc.CreatePolygonGroup();
		GroupSlot[G] = Slot;
		Groups.Add(G);
		UMaterialInterface* Material = MaterialPaths.IsValidIndex(S) ? LoadObject<UMaterialInterface>(nullptr, *MaterialPaths[S]) : nullptr;
		if (MaterialPaths.IsValidIndex(S) && !Material)
		{
			UE_LOG(LogTemp, Warning, TEXT("Materyal yok: %s"), *MaterialPaths[S]);
		}
		Mesh->GetStaticMaterials().Add(FStaticMaterial(Material, Slot, Slot));
	}

	for (uint32 T = 0; T < NumTris; ++T)
	{
		const uint32 A = Idx[T * 3], B = Idx[T * 3 + 1], C = Idx[T * 3 + 2];
		if (A >= NumVerts || B >= NumVerts || C >= NumVerts || A == B || B == C || A == C)
		{
			continue;
		}
		const FPolygonGroupID G = Groups[FMath::Min<int32>(Mat[T], NumSlots - 1)];
		TArray<FVertexInstanceID, TInlineAllocator<3>> Corners = { Instances[A], Instances[B], Instances[C] };
		Desc.CreateTriangle(G, Corners);
	}

	FStaticMeshSourceModel& Source = Mesh->AddSourceModel();
	Source.BuildSettings.bRecomputeNormals = false;
	Source.BuildSettings.bRecomputeTangents = true;
	Source.BuildSettings.bUseMikkTSpace = true;
	Source.BuildSettings.bGenerateLightmapUVs = false;
	Source.BuildSettings.bRemoveDegenerates = true;
	Source.BuildSettings.bUseFullPrecisionUVs = true;
	Source.BuildSettings.DistanceFieldResolutionScale = bDistanceField ? 1.f : 0.f;
	Mesh->CreateMeshDescription(0, MoveTemp(Desc));
	Mesh->CommitMeshDescription(0);

	FMeshNaniteSettings Nanite = Mesh->GetNaniteSettings();
	Nanite.bEnabled = bNanite;
	// Carpisma ve Nanite olmayan yollar icin tam cozunurluklu yedek
	Nanite.FallbackPercentTriangles = CollisionMode == 1 ? 1.f : 0.1f;
	Mesh->SetNaniteSettings(Nanite);

	Mesh->SetLightingGuid();
	Mesh->CreateBodySetup();
	UBodySetup* Body = Mesh->GetBodySetup();
	Body->AggGeom.EmptyElements();
	if (CollisionMode == 1)
	{
		Body->CollisionTraceFlag = CTF_UseComplexAsSimple;
	}
	else
	{
		Body->CollisionTraceFlag = CTF_UseDefault;
	}
	Mesh->Build(true);
	if (CollisionMode == 2)
	{
		const FBox Bounds = Mesh->GetBoundingBox();
		FKBoxElem Box(Bounds.GetSize().X, Bounds.GetSize().Y, Bounds.GetSize().Z);
		Box.Center = Bounds.GetCenter();
		Body->AggGeom.BoxElems.Add(Box);
		Body->InvalidatePhysicsData();
		Body->CreatePhysicsMeshes();
	}
	Mesh->PostEditChange();
	Mesh->MarkPackageDirty();
	FAssetRegistryModule::AssetCreated(Mesh);

	FSavePackageArgs Args;
	Args.TopLevelFlags = RF_Public | RF_Standalone;
	const FString Disk = FPackageName::LongPackageNameToFilename(AssetPath, FPackageName::GetAssetPackageExtension());
	return UPackage::SavePackage(Package, Mesh, *Disk, Args);
#else
	return false;
#endif
}

bool UKapadokyaBuildLib::BakeHumanPose(const FString& BodyPath, const FString& OutfitPath, const FString& FacePath, const FString& HairPath, int32 Lod, int32 PoseId, const FString& OutFile)
{
#if WITH_EDITOR
	USkeletalMesh* Body = LoadObject<USkeletalMesh>(nullptr, *BodyPath);
	USkeletalMesh* Outfit = LoadObject<USkeletalMesh>(nullptr, *OutfitPath);
	USkeletalMesh* Face = LoadObject<USkeletalMesh>(nullptr, *FacePath);
	if (!Body || !Outfit || !Face)
	{
		UE_LOG(LogTemp, Error, TEXT("BakeHumanPose: mesh yok"));
		return false;
	}
	const FReferenceSkeleton& Ref = Body->GetRefSkeleton();
	const int32 NumBones = Ref.GetNum();
	TArray<FTransform> RefCS, PoseCS;
	RefCS.SetNum(NumBones);
	PoseCS.SetNum(NumBones);
	for (int32 I = 0; I < NumBones; ++I)
	{
		const int32 Parent = Ref.GetParentIndex(I);
		RefCS[I] = Parent >= 0 ? Ref.GetRefBonePose()[I] * RefCS[Parent] : Ref.GetRefBonePose()[I];
	}
	// Kol yonleri: X sol (kemik _l +X), Y on, Z yukari. Yonler aci degil hedef vektor.
	struct FAim { FName Bone; FName Child; FVector Dir; };
	TArray<FAim> Aims;
	const auto Arm = [&Aims](const TCHAR* Side, double Sign, const FVector& Upper, const FVector& Lower)
	{
		const FString S(Side);
		Aims.Add({ FName(TEXT("upperarm_") + S), FName(TEXT("lowerarm_") + S), FVector(Upper.X * Sign, Upper.Y, Upper.Z).GetSafeNormal() });
		Aims.Add({ FName(TEXT("lowerarm_") + S), FName(TEXT("hand_") + S), FVector(Lower.X * Sign, Lower.Y, Lower.Z).GetSafeNormal() });
	};
	const FVector DownU(0.14, 0.04, -1.0), DownL(0.05, 0.28, -1.0), UpU(0.42, 0.10, 0.9), UpL(0.10, 0.12, 1.0), FrontU(0.10, 0.55, -0.85), FrontL(-0.05, 0.95, -0.25);
	switch (PoseId)
	{
	case 1: Arm(TEXT("l"), 1.0, UpU, UpL); Arm(TEXT("r"), -1.0, UpU, UpL); break;
	case 2: Arm(TEXT("l"), 1.0, UpU, UpL); Arm(TEXT("r"), -1.0, DownU, DownL); break;
	case 3: Arm(TEXT("l"), 1.0, FrontU, FrontL); Arm(TEXT("r"), -1.0, FrontU, FrontL); break;
	default: Arm(TEXT("l"), 1.0, DownU, DownL); Arm(TEXT("r"), -1.0, DownU, DownL); break;
	}
	for (int32 I = 0; I < NumBones; ++I)
	{
		const int32 Parent = Ref.GetParentIndex(I);
		PoseCS[I] = Parent >= 0 ? Ref.GetRefBonePose()[I] * PoseCS[Parent] : Ref.GetRefBonePose()[I];
		for (const FAim& A : Aims)
		{
			if (Ref.GetBoneName(I) == A.Bone)
			{
				const int32 Child = Ref.FindBoneIndex(A.Child);
				if (Child != INDEX_NONE)
				{
					const FVector RefDir = (RefCS[Child].GetLocation() - RefCS[I].GetLocation()).GetSafeNormal();
					PoseCS[I].SetRotation(FQuat::FindBetweenNormals(RefDir, A.Dir) * RefCS[I].GetRotation());
				}
			}
		}
	}
	TArray<FMatrix> Skin;
	Skin.SetNum(NumBones);
	for (int32 I = 0; I < NumBones; ++I)
	{
		Skin[I] = RefCS[I].ToMatrixWithScale().Inverse() * PoseCS[I].ToMatrixWithScale();
	}

	TArray<FVector3f> OutPos, OutNor;
	TArray<FVector2f> OutUv;
	TArray<uint32> OutIdx;
	TArray<uint8> OutMat;
	const auto SlotOf = [](const FString& Name) -> int32
	{
		if (Name.Contains(TEXT("Shirt"))) return 1;
		if (Name.Contains(TEXT("Short"))) return 2;
		if (Name.Contains(TEXT("body"))) return 0;
		if (Name.Contains(TEXT("head_"))) return 3;
		if (Name.Contains(TEXT("teeth"))) return 4;
		if (Name.Contains(TEXT("eyeLeft"))) return 5;
		if (Name.Contains(TEXT("eyeRight"))) return 6;
		return -1;
	};
	for (USkeletalMesh* Mesh : { Body, Outfit, Face })
	{
		const int32 UseLod = FMath::Min(Lod, Mesh->GetLODNum() - 1);
		const FMeshDescription* Md = Mesh->GetMeshDescription(UseLod);
		if (!Md)
		{
			UE_LOG(LogTemp, Error, TEXT("BakeHumanPose: mesh tanimi yok %s"), *Mesh->GetName());
			return false;
		}
		FSkeletalMeshConstAttributes Attr(*Md);
		TVertexAttributesConstRef<FVector3f> Pos = Attr.GetVertexPositions();
		TVertexInstanceAttributesConstRef<FVector3f> Nor = Attr.GetVertexInstanceNormals();
		TVertexInstanceAttributesConstRef<FVector2f> Uvs = Attr.GetVertexInstanceUVs();
		TPolygonGroupAttributesConstRef<FName> Slots = Attr.GetPolygonGroupMaterialSlotNames();
		FSkinWeightsVertexAttributesConstRef Weights = Attr.GetVertexSkinWeights();
		// Kemik adiyla govde iskeletine esle; yuzun kendi kemikleri hareket etmez
		const FReferenceSkeleton& MeshRef = Mesh->GetRefSkeleton();
		TArray<int32> BoneMap;
		BoneMap.SetNum(MeshRef.GetNum());
		for (int32 B = 0; B < MeshRef.GetNum(); ++B)
		{
			BoneMap[B] = Ref.FindBoneIndex(MeshRef.GetBoneName(B));
		}
		TMap<FVertexInstanceID, uint32> Remap;
		for (const FTriangleID Tri : Md->Triangles().GetElementIDs())
		{
			const FPolygonGroupID G = Md->GetTrianglePolygonGroup(Tri);
			const int32 Slot = SlotOf(Slots[G].ToString());
			if (Slot < 0)
			{
				continue;
			}
			TArrayView<const FVertexInstanceID> Corners = Md->GetTriangleVertexInstances(Tri);
			for (const FVertexInstanceID Vi : Corners)
			{
				uint32* Found = Remap.Find(Vi);
				if (!Found)
				{
					const FVertexID V = Md->GetVertexInstanceVertex(Vi);
					FVector P = FVector(Pos[V]);
					FVector N = FVector(Nor[Vi]);
					FVector Sp = FVector::ZeroVector, Sn = FVector::ZeroVector;
					double Sum = 0.0;
					for (const UE::AnimationCore::FBoneWeight& W : Weights.Get(V))
					{
						const int32 B = MeshRef.IsValidIndex(W.GetBoneIndex()) ? BoneMap[W.GetBoneIndex()] : INDEX_NONE;
						const FMatrix& M = B != INDEX_NONE ? Skin[B] : FMatrix::Identity;
						const double Wt = W.GetWeight();
						Sp += M.TransformPosition(P) * Wt;
						Sn += M.TransformVector(N) * Wt;
						Sum += Wt;
					}
					if (Sum > 1e-6)
					{
						P = Sp / Sum;
						N = Sn.GetSafeNormal();
					}
					Found = &Remap.Add(Vi, uint32(OutPos.Num()));
					OutPos.Add(FVector3f(P));
					OutNor.Add(FVector3f(N));
					OutUv.Add(Uvs.Get(Vi, 0));
				}
				OutIdx.Add(*Found);
			}
			OutMat.Add(uint8(Slot));
		}
	}
	// Sac kartlari: bas kemigi hareket etmedigi icin dogrudan eklenir
	if (UStaticMesh* Hair = HairPath.IsEmpty() ? nullptr : LoadObject<UStaticMesh>(nullptr, *HairPath))
	{
		if (const FMeshDescription* Md = Hair->GetMeshDescription(0))
		{
			FStaticMeshConstAttributes Attr(*Md);
			TVertexAttributesConstRef<FVector3f> Pos = Attr.GetVertexPositions();
			TVertexInstanceAttributesConstRef<FVector3f> Nor = Attr.GetVertexInstanceNormals();
			TVertexInstanceAttributesConstRef<FVector2f> Uvs = Attr.GetVertexInstanceUVs();
			TMap<FVertexInstanceID, uint32> Remap;
			for (const FTriangleID Tri : Md->Triangles().GetElementIDs())
			{
				for (const FVertexInstanceID Vi : Md->GetTriangleVertexInstances(Tri))
				{
					uint32* Found = Remap.Find(Vi);
					if (!Found)
					{
						Found = &Remap.Add(Vi, uint32(OutPos.Num()));
						OutPos.Add(Pos[Md->GetVertexInstanceVertex(Vi)]);
						OutNor.Add(Nor[Vi]);
						OutUv.Add(Uvs.Get(Vi, 0));
					}
					OutIdx.Add(*Found);
				}
				OutMat.Add(7);
			}
		}
	}
	// KMSH yaz
	TArray<uint8> Out;
	const auto Put = [&Out](const void* Data, int64 Size) { Out.Append(static_cast<const uint8*>(Data), Size); };
	Put("KMS1", 4);
	const uint32 Nv = OutPos.Num(), Nt = OutMat.Num();
	Put(&Nv, 4);
	Put(&Nt, 4);
	Put(OutPos.GetData(), Nv * 12);
	Put(OutNor.GetData(), Nv * 12);
	Put(OutUv.GetData(), Nv * 8);
	TArray<uint8> Zero;
	Zero.SetNumZeroed(Nv * 8);
	Put(Zero.GetData(), Zero.Num());
	TArray<uint8> White;
	White.Init(255, Nv * 4);
	Put(White.GetData(), White.Num());
	Put(OutIdx.GetData(), OutIdx.Num() * 4);
	Put(OutMat.GetData(), OutMat.Num());
	UE_LOG(LogTemp, Display, TEXT("BakeHumanPose %s: %u kose %u ucgen"), *OutFile, Nv, Nt);
	return FFileHelper::SaveArrayToFile(Out, *OutFile);
#else
	return false;
#endif
}

