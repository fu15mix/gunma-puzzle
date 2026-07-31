import { highwayOverlaysByPuzzleId } from "./highwayOverlays";
import { roadPoisByPuzzleId } from "./roadPois";
import { anjoSchoolPieces } from "./anjoSchoolPieces";
import { aichiPieces } from "./aichiPieces";
import { isesakiSchoolTownPuzzles } from "./isesakiSchoolTownPuzzles";
import { isesakiSchoolPieces } from "./isesakiSchoolPieces";
import { miyagoTownPieces } from "./miyagoTownPieces";
import { initialPieces, type Piece } from "./pieces";

export type MapOverlay = {
  id: string;
  name: string;
  path: string;
};

export type MapPoi = {
  id: string;
  kind: "ic" | "sa" | "pa";
  name: string;
  x: number;
  y: number;
};

export type PuzzleConfig = {
  id: string;
  title: string;
  eyebrow: string;
  modeLabel: string;
  pieces: Piece[];
  overlays?: MapOverlay[];
  pois?: MapPoi[];
  snapDistance: number;
  note?: string;
};

const basePuzzles: PuzzleConfig[] = [
  {
    id: "gunma-municipalities",
    title: "ぐんま市町村パズル",
    eyebrow: "こどもとあそべる Web パズル",
    modeLabel: "群馬県市町村",
    pieces: initialPieces,
    snapDistance: 42,
  },
  {
    id: "aichi-municipalities",
    title: "愛知県市町村パズル",
    eyebrow: "愛知県 Ver.",
    modeLabel: "愛知県市町村",
    pieces: aichiPieces,
    snapDistance: 38,
  },
  {
    id: "anjo-schools",
    title: "安城市小学校区パズル",
    eyebrow: "安城市 Ver.",
    modeLabel: "安城市小学校区",
    pieces: anjoSchoolPieces,
    snapDistance: 34,
    note: "小学校区は町丁・字境界をもとにした概略版です。",
  },
  {
    id: "isesaki-schools",
    title: "伊勢崎市小学校区パズル",
    eyebrow: "伊勢崎市 Ver.",
    modeLabel: "伊勢崎市小学校区",
    pieces: isesakiSchoolPieces,
    snapDistance: 34,
    note: "小学校区は町丁境界をもとにした概略版です。",
  },
  {
    id: "miyago-towns",
    title: "宮郷・宮郷第二 町名パズル",
    eyebrow: "伊勢崎市 Ver.",
    modeLabel: "宮郷町名",
    pieces: miyagoTownPieces,
    snapDistance: 38,
    note: "町名境界をもとにした宮郷・宮郷第二エリアの町名版です。",
  },
  ...isesakiSchoolTownPuzzles,
];

export const puzzles: PuzzleConfig[] = basePuzzles.map((puzzle) => ({
  ...puzzle,
  overlays: highwayOverlaysByPuzzleId[puzzle.id] ?? [],
  pois: roadPoisByPuzzleId[puzzle.id] ?? [],
}));
