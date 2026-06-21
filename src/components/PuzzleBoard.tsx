import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { SNAP_DISTANCE, type Piece } from "../data/pieces";

type PuzzleBoardProps = {
  pieces: Piece[];
  onPiecesChange: (nextPieces: Piece[]) => void;
};

type DragState = {
  id: string;
  pointerId: number;
  anchorX: number;
  anchorY: number;
  mapX: number;
  mapY: number;
};

const VIEWBOX_X = 45;
const VIEWBOX_Y = 8;
const VIEWBOX_WIDTH = 710;
const VIEWBOX_HEIGHT = 584;

function getSvgPoint(svg: SVGSVGElement, clientX: number, clientY: number) {
  const ctm = svg.getScreenCTM();
  if (!ctm) {
    return null;
  }

  const point = new DOMPoint(clientX, clientY).matrixTransform(ctm.inverse());

  return {
    x: point.x,
    y: point.y,
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export default function PuzzleBoard({
  pieces,
  onPiecesChange,
}: PuzzleBoardProps) {
  const mapRef = useRef<SVGSVGElement | null>(null);
  const [dragState, setDragState] = useState<DragState | null>(null);

  useEffect(() => {
    if (!dragState) {
      return;
    }

    const handlePointerMove = (event: PointerEvent) => {
      if (event.pointerId !== dragState.pointerId) {
        return;
      }

      const svg = mapRef.current;
      if (!svg) {
        return;
      }

      const point = getSvgPoint(svg, event.clientX, event.clientY);
      if (!point) {
        return;
      }

      setDragState((current) =>
        current
          ? {
              ...current,
              mapX: point.x,
              mapY: point.y,
            }
          : null,
      );
    };

    const handlePointerUp = (event: PointerEvent) => {
      if (event.pointerId !== dragState.pointerId) {
        return;
      }

      const piece = pieces.find((candidate) => candidate.id === dragState.id);
      const svg = mapRef.current;

      if (!piece || !svg) {
        setDragState(null);
        return;
      }

      const dropPoint = getSvgPoint(svg, event.clientX, event.clientY);
      if (!dropPoint) {
        setDragState(null);
        return;
      }

      const dropX = dropPoint.x - dragState.anchorX;
      const dropY = dropPoint.y - dragState.anchorY;
      const distance = Math.sqrt(
        (dropX - piece.correctX) ** 2 + (dropY - piece.correctY) ** 2,
      );

      if (distance <= SNAP_DISTANCE) {
        onPiecesChange(
          pieces.map((candidate) =>
            candidate.id === piece.id
              ? {
                  ...candidate,
                  currentX: candidate.correctX,
                  currentY: candidate.correctY,
                  placed: true,
                }
              : candidate,
          ),
        );
      }

      setDragState(null);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [dragState, onPiecesChange, pieces]);

  const handleTrayPointerDown =
    (piece: Piece) => (event: ReactPointerEvent<SVGSVGElement>) => {
      event.preventDefault();

      const trayPoint = getSvgPoint(
        event.currentTarget,
        event.clientX,
        event.clientY,
      );
      const mapPoint = mapRef.current
        ? getSvgPoint(mapRef.current, event.clientX, event.clientY)
        : null;

      if (!trayPoint || !mapPoint) {
        return;
      }

      setDragState({
        id: piece.id,
        pointerId: event.pointerId,
        anchorX: clamp(trayPoint.x, 0, piece.width),
        anchorY: clamp(trayPoint.y, 0, piece.height),
        mapX: mapPoint.x,
        mapY: mapPoint.y,
      });
    };

  const draggingPiece = dragState
    ? pieces.find((piece) => piece.id === dragState.id) ?? null
    : null;

  const unplacedPieces = pieces.filter((piece) => !piece.placed);

  return (
    <div className="play-area">
      <div className="map-frame">
        <svg
          ref={mapRef}
          className="puzzle-board"
          viewBox={`${VIEWBOX_X} ${VIEWBOX_Y} ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
          role="img"
          aria-label="群馬県市町村パズル"
        >
          <rect
            x="48"
            y="12"
            width="704"
            height="576"
            rx="28"
            className="board-surface"
          />

          {pieces.map((piece) => (
            <g
              key={`guide-${piece.id}`}
              transform={`translate(${piece.correctX} ${piece.correctY})`}
            >
              <path d={piece.path} className="piece-guide" />
            </g>
          ))}

          {pieces
            .filter((piece) => piece.placed)
            .map((piece) => (
              <g
                key={piece.id}
                transform={`translate(${piece.currentX} ${piece.currentY})`}
                className="piece-group is-placed"
              >
                <path d={piece.path} className="piece-shape" />
              </g>
            ))}

          {draggingPiece && dragState ? (
            <g
              transform={`translate(${dragState.mapX - dragState.anchorX} ${
                dragState.mapY - dragState.anchorY
              })`}
              className="piece-group is-dragging"
            >
              <path d={draggingPiece.path} className="piece-shape" />
            </g>
          ) : null}
        </svg>
      </div>

      <div className="tray-panel">
        <div className="tray-header">
          <p className="tray-label">市町村ピース置き場</p>
          <p className="tray-help">左右にスクロールしてピースを選ぶ</p>
        </div>

        <div className="tray-scroll">
          <div className="tray-row">
            {unplacedPieces.map((piece) => (
              <button key={piece.id} type="button" className="tray-piece-card">
                <span className="tray-piece-figure">
                  <svg
                    className="tray-piece-svg"
                    viewBox={`0 0 ${piece.width} ${piece.height}`}
                    onPointerDown={handleTrayPointerDown(piece)}
                  >
                    <g className="piece-group">
                      <path d={piece.path} className="piece-shape" />
                    </g>
                  </svg>
                </span>
                <span className="tray-piece-text">
                  <span className="tray-piece-reading">{piece.reading}</span>
                  <span className="tray-piece-name">{piece.name}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
