import { useEffect, useRef, useState } from "react";
import type {
  PointerEvent as ReactPointerEvent,
  TouchEvent as ReactTouchEvent,
} from "react";
import type { Piece } from "../data/pieces";

type PuzzleBoardProps = {
  pieces: Piece[];
  onPiecesChange: (nextPieces: Piece[]) => void;
  onGameStart: () => void;
  snapDistance: number;
  note?: string;
};

type DragState = {
  id: string;
  pointerId: number | null;
  anchorX: number;
  anchorY: number;
  mapX: number;
  mapY: number;
};

const VIEWBOX_X = 60;
const VIEWBOX_Y = 18;
const VIEWBOX_WIDTH = 680;
const VIEWBOX_HEIGHT = 560;

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
  onGameStart,
  snapDistance,
  note,
}: PuzzleBoardProps) {
  const mapRef = useRef<SVGSVGElement | null>(null);
  const [dragState, setDragState] = useState<DragState | null>(null);

  useEffect(() => {
    if (!dragState) {
      return;
    }

    const updateDragPosition = (clientX: number, clientY: number) => {
      const svg = mapRef.current;
      if (!svg) {
        return;
      }

      const point = getSvgPoint(svg, clientX, clientY);
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

    const finishDrag = (clientX: number, clientY: number) => {
      const piece = pieces.find((candidate) => candidate.id === dragState.id);
      const svg = mapRef.current;

      if (!piece || !svg) {
        setDragState(null);
        return;
      }

      const dropPoint = getSvgPoint(svg, clientX, clientY);
      if (!dropPoint) {
        setDragState(null);
        return;
      }

      const dropX = dropPoint.x - dragState.anchorX;
      const dropY = dropPoint.y - dragState.anchorY;
      const distance = Math.sqrt(
        (dropX - piece.correctX) ** 2 + (dropY - piece.correctY) ** 2,
      );

      if (distance <= snapDistance) {
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

    const handlePointerMove = (event: PointerEvent) => {
      if (event.pointerId !== dragState.pointerId) {
        return;
      }

      updateDragPosition(event.clientX, event.clientY);
    };

    const handlePointerUp = (event: PointerEvent) => {
      if (event.pointerId !== dragState.pointerId) {
        return;
      }

      finishDrag(event.clientX, event.clientY);
    };

    const handleTouchMove = (event: TouchEvent) => {
      if (dragState.pointerId !== null) {
        return;
      }

      const touch = event.touches[0];
      if (!touch) {
        return;
      }

      event.preventDefault();
      updateDragPosition(touch.clientX, touch.clientY);
    };

    const handleTouchEnd = (event: TouchEvent) => {
      if (dragState.pointerId !== null) {
        return;
      }

      const touch = event.changedTouches[0];
      if (!touch) {
        setDragState(null);
        return;
      }

      event.preventDefault();
      finishDrag(touch.clientX, touch.clientY);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);
    window.addEventListener("touchmove", handleTouchMove, { passive: false });
    window.addEventListener("touchend", handleTouchEnd, { passive: false });
    window.addEventListener("touchcancel", handleTouchEnd, { passive: false });

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleTouchEnd);
      window.removeEventListener("touchcancel", handleTouchEnd);
    };
  }, [dragState, onPiecesChange, pieces]);

  const startDrag = (
    piece: Piece,
    traySvg: SVGSVGElement,
    clientX: number,
    clientY: number,
    pointerId: number | null,
  ) => {
    const trayPoint = getSvgPoint(traySvg, clientX, clientY);
    const mapPoint = mapRef.current
      ? getSvgPoint(mapRef.current, clientX, clientY)
      : null;

    if (!trayPoint || !mapPoint) {
      return;
    }

    onGameStart();

    setDragState({
      id: piece.id,
      pointerId,
      anchorX: clamp(trayPoint.x, 0, piece.width),
      anchorY: clamp(trayPoint.y, 0, piece.height),
      mapX: mapPoint.x,
      mapY: mapPoint.y,
    });
  };

  const handleTrayPointerDown =
    (piece: Piece) => (event: ReactPointerEvent<SVGSVGElement>) => {
      if (event.pointerType === "touch") {
        return;
      }

      event.preventDefault();
      event.currentTarget.setPointerCapture(event.pointerId);
      startDrag(
        piece,
        event.currentTarget,
        event.clientX,
        event.clientY,
        event.pointerId,
      );
    };

  const handleTrayTouchStart =
    (piece: Piece) => (event: ReactTouchEvent<SVGSVGElement>) => {
      const touch = event.touches[0];
      if (!touch) {
        return;
      }

      event.preventDefault();
      startDrag(
        piece,
        event.currentTarget,
        touch.clientX,
        touch.clientY,
        null,
      );
    };

  const draggingPiece = dragState
    ? pieces.find((piece) => piece.id === dragState.id) ?? null
    : null;

  const unplacedPieces = pieces.filter((piece) => !piece.placed);

  return (
    <div className="play-area">
      <div className="map-frame">
        {note ? <p className="map-note">{note}</p> : null}
        <svg
          ref={mapRef}
          className="puzzle-board"
          viewBox={`${VIEWBOX_X} ${VIEWBOX_Y} ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
          role="img"
          aria-label="群馬県市町村パズル"
        >
          <rect
            x="62"
            y="20"
            width="676"
            height="556"
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
                    onTouchStart={handleTrayTouchStart(piece)}
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
