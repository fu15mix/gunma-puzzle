import { useEffect, useRef, useState } from "react";
import type {
  PointerEvent as ReactPointerEvent,
  TouchEvent as ReactTouchEvent,
} from "react";
import type { MapOverlay, MapPoi } from "../data/puzzles";
import type { Piece } from "../data/pieces";

type PuzzleBoardProps = {
  pieces: Piece[];
  overlays?: MapOverlay[];
  pois?: MapPoi[];
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

type ViewCenter = {
  x: number;
  y: number;
};

type PanState = {
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startCenterX: number;
  startCenterY: number;
};

const VIEWBOX_X = 60;
const VIEWBOX_Y = 18;
const VIEWBOX_WIDTH = 680;
const VIEWBOX_HEIGHT = 560;
const MIN_VIEW_SCALE = 1;
const DEFAULT_VIEW_SCALE = 1.18;
const MAX_VIEW_SCALE = 3;
const VIEW_SCALE_STEP = 0.28;
const DEFAULT_VIEW_CENTER = {
  x: VIEWBOX_X + VIEWBOX_WIDTH / 2,
  y: VIEWBOX_Y + VIEWBOX_HEIGHT / 2,
};

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

function clampViewCenter(center: ViewCenter, scale: number): ViewCenter {
  const viewWidth = VIEWBOX_WIDTH / scale;
  const viewHeight = VIEWBOX_HEIGHT / scale;

  if (scale <= MIN_VIEW_SCALE || viewWidth >= VIEWBOX_WIDTH) {
    return DEFAULT_VIEW_CENTER;
  }

  return {
    x: clamp(
      center.x,
      VIEWBOX_X + viewWidth / 2,
      VIEWBOX_X + VIEWBOX_WIDTH - viewWidth / 2,
    ),
    y: clamp(
      center.y,
      VIEWBOX_Y + viewHeight / 2,
      VIEWBOX_Y + VIEWBOX_HEIGHT - viewHeight / 2,
    ),
  };
}

export default function PuzzleBoard({
  pieces,
  overlays = [],
  pois = [],
  onPiecesChange,
  onGameStart,
  snapDistance,
  note,
}: PuzzleBoardProps) {
  const mapRef = useRef<SVGSVGElement | null>(null);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [panState, setPanState] = useState<PanState | null>(null);
  const [viewScale, setViewScale] = useState(DEFAULT_VIEW_SCALE);
  const [viewCenter, setViewCenter] =
    useState<ViewCenter>(DEFAULT_VIEW_CENTER);
  const [showHighways, setShowHighways] = useState(true);
  const [showPois, setShowPois] = useState(true);
  const [selectedPoi, setSelectedPoi] = useState<MapPoi | null>(null);

  useEffect(() => {
    setSelectedPoi(null);
    setPanState(null);
    setViewScale(DEFAULT_VIEW_SCALE);
    setViewCenter(DEFAULT_VIEW_CENTER);
  }, [pois]);

  useEffect(() => {
    if (!showPois) {
      setSelectedPoi(null);
    }
  }, [showPois]);

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

  useEffect(() => {
    if (!panState) {
      return;
    }

    const handlePointerMove = (event: PointerEvent) => {
      if (event.pointerId !== panState.pointerId) {
        return;
      }

      const svg = mapRef.current;
      const rect = svg?.getBoundingClientRect();
      if (!rect || rect.width === 0 || rect.height === 0) {
        return;
      }

      const viewWidth = VIEWBOX_WIDTH / viewScale;
      const viewHeight = VIEWBOX_HEIGHT / viewScale;
      const nextCenter = {
        x:
          panState.startCenterX -
          (event.clientX - panState.startClientX) * (viewWidth / rect.width),
        y:
          panState.startCenterY -
          (event.clientY - panState.startClientY) * (viewHeight / rect.height),
      };

      setViewCenter(clampViewCenter(nextCenter, viewScale));
    };

    const handlePointerUp = (event: PointerEvent) => {
      if (event.pointerId === panState.pointerId) {
        setPanState(null);
      }
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [panState, viewScale]);

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

  const changeViewScale = (nextScale: number) => {
    const scale = clamp(nextScale, MIN_VIEW_SCALE, MAX_VIEW_SCALE);
    setViewScale(scale);
    setViewCenter((current) => clampViewCenter(current, scale));
  };

  const resetView = () => {
    setViewScale(MIN_VIEW_SCALE);
    setViewCenter(DEFAULT_VIEW_CENTER);
  };

  const handleMapPointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (viewScale <= MIN_VIEW_SCALE || dragState || event.button !== 0) {
      return;
    }

    event.preventDefault();
    setSelectedPoi(null);
    event.currentTarget.setPointerCapture(event.pointerId);
    setPanState({
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startCenterX: viewCenter.x,
      startCenterY: viewCenter.y,
    });
  };

  const draggingPiece = dragState
    ? pieces.find((piece) => piece.id === dragState.id) ?? null
    : null;

  const unplacedPieces = pieces.filter((piece) => !piece.placed);
  const tooltipWidth = selectedPoi
    ? Math.max(86, Math.min(220, selectedPoi.name.length * 13 + 24))
    : 0;
  const tooltipX = selectedPoi
    ? clamp(
        selectedPoi.x + 10,
        VIEWBOX_X + 12,
        VIEWBOX_X + VIEWBOX_WIDTH - tooltipWidth - 12,
      )
    : 0;
  const tooltipY = selectedPoi
    ? clamp(selectedPoi.y - 34, VIEWBOX_Y + 14, VIEWBOX_Y + VIEWBOX_HEIGHT - 34)
    : 0;
  const viewBoxWidth = VIEWBOX_WIDTH / viewScale;
  const viewBoxHeight = VIEWBOX_HEIGHT / viewScale;
  const viewBoxX = clamp(
    viewCenter.x - viewBoxWidth / 2,
    VIEWBOX_X,
    VIEWBOX_X + VIEWBOX_WIDTH - viewBoxWidth,
  );
  const viewBoxY = clamp(
    viewCenter.y - viewBoxHeight / 2,
    VIEWBOX_Y,
    VIEWBOX_Y + VIEWBOX_HEIGHT - viewBoxHeight,
  );
  const visibleOverlays = showHighways ? overlays : [];
  const visiblePois = showPois ? pois : [];

  return (
    <div className="play-area">
      <div className="map-frame">
        {note ? <p className="map-note">{note}</p> : null}
        {visibleOverlays.length > 0 || visiblePois.length > 0 ? (
          <p className="map-attribution">道路情報: © OpenStreetMap contributors</p>
        ) : null}
        <div className="map-controls" aria-label="地図表示">
          <div className="map-control-group">
            <button
              type="button"
              onClick={() => changeViewScale(viewScale - VIEW_SCALE_STEP)}
              aria-label="地図を縮小"
            >
              −
            </button>
            <button type="button" onClick={resetView}>
              全体
            </button>
            <button
              type="button"
              onClick={() => changeViewScale(viewScale + VIEW_SCALE_STEP)}
              aria-label="地図を拡大"
            >
              ＋
            </button>
          </div>
          <div className="map-control-group">
            {overlays.length > 0 ? (
              <button
                type="button"
                className={showHighways ? "is-active" : ""}
                onClick={() => setShowHighways((current) => !current)}
                aria-pressed={showHighways}
              >
                高速道路
              </button>
            ) : null}
            {pois.length > 0 ? (
              <button
                type="button"
                className={showPois ? "is-active" : ""}
                onClick={() => setShowPois((current) => !current)}
                aria-pressed={showPois}
              >
                IC/SA/PA
              </button>
            ) : null}
          </div>
        </div>
        {viewScale > MIN_VIEW_SCALE ? (
          <p className="map-pan-hint">地図をドラッグして移動</p>
        ) : null}
        <svg
          ref={mapRef}
          className="puzzle-board"
          viewBox={`${viewBoxX} ${viewBoxY} ${viewBoxWidth} ${viewBoxHeight}`}
          onPointerDown={handleMapPointerDown}
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

          {visibleOverlays.map((overlay) => (
            <path
              key={overlay.id}
              d={overlay.path}
              className="map-overlay-highway"
            >
              <title>{overlay.name}</title>
            </path>
          ))}

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

          {visiblePois.map((poi) => (
            <g
              key={poi.id}
              className={`map-poi map-poi-${poi.kind}`}
              transform={`translate(${poi.x} ${poi.y})`}
              onPointerDown={(event) => {
                event.preventDefault();
                event.stopPropagation();
                setSelectedPoi(poi);
              }}
            >
              {poi.kind === "ic" ? <circle r="4.6" /> : null}
              {poi.kind === "sa" ? (
                <rect x="-4.8" y="-4.8" width="9.6" height="9.6" rx="2.2" />
              ) : null}
              {poi.kind === "pa" ? (
                <path d="M0 -5.6 L5.6 4.8 L-5.6 4.8 Z" />
              ) : null}
            </g>
          ))}

          {selectedPoi ? (
            <g
              className="map-poi-tooltip"
              transform={`translate(${tooltipX} ${tooltipY})`}
            >
              <rect width={tooltipWidth} height="28" rx="14" />
              <text x="12" y="19">
                {selectedPoi.name}
              </text>
            </g>
          ) : null}

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
                  {piece.reading && piece.reading !== piece.name ? (
                    <span className="tray-piece-reading">{piece.reading}</span>
                  ) : null}
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
