import { useMemo, useState } from "react";
import PuzzleBoard from "./components/PuzzleBoard";
import { initialPieces, type Piece } from "./data/pieces";

function shufflePieces(pieces: Piece[]): Piece[] {
  const nextPieces = [...pieces];

  for (let index = nextPieces.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [nextPieces[index], nextPieces[randomIndex]] = [
      nextPieces[randomIndex],
      nextPieces[index],
    ];
  }

  return nextPieces;
}

function resetPieces(): Piece[] {
  return shufflePieces(initialPieces.map((piece) => ({ ...piece })));
}

export default function App() {
  const [pieces, setPieces] = useState<Piece[]>(() => resetPieces());

  const placedCount = useMemo(
    () => pieces.filter((piece) => piece.placed).length,
    [pieces],
  );
  const isCleared = useMemo(
    () => pieces.every((piece) => piece.placed),
    [pieces],
  );

  return (
    <main className="app">
      <section className="app-card">
        <header className="app-header">
          <div>
            <p className="eyebrow">こどもとあそべる Web パズル</p>
            <h1>ぐんま市町村パズル</h1>
          </div>

          <div className="status-panel">
            <p className="status-count">
              正解 <strong>{placedCount}</strong> / {pieces.length}
            </p>
            <button
              type="button"
              className="reset-button"
              onClick={() => setPieces(resetPieces())}
            >
              リセット
            </button>
          </div>
        </header>

        {isCleared ? (
          <div className="clear-banner" aria-live="polite">
            クリア！
          </div>
        ) : null}

        <PuzzleBoard pieces={pieces} onPiecesChange={setPieces} />
      </section>
    </main>
  );
}
