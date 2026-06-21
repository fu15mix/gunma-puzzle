import { isesakiSchoolPieces } from "./isesakiSchoolPieces";
import { initialPieces, type Piece } from "./pieces";

export type PuzzleConfig = {
  id: string;
  title: string;
  eyebrow: string;
  modeLabel: string;
  pieces: Piece[];
  snapDistance: number;
  note?: string;
};

export const puzzles: PuzzleConfig[] = [
  {
    id: "gunma-municipalities",
    title: "ぐんま市町村パズル",
    eyebrow: "こどもとあそべる Web パズル",
    modeLabel: "群馬県市町村",
    pieces: initialPieces,
    snapDistance: 42,
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
];
