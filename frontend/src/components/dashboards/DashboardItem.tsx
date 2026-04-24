"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button } from "@/components/ui/button";
import type { DashboardItem as DashboardItemType } from "@/hooks/useDashboards";

interface DashboardItemProps {
  item: DashboardItemType;
  onRemove: (widgetId: string) => void;
}

export function DashboardItem({ item, onRemove }: DashboardItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.widget_id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    gridColumn: `span ${item.width}`,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-card border border-border rounded-lg flex flex-col min-h-[140px]"
      data-role="dashboard-item"
      data-widget-id={item.widget_id}
      data-grid-width={item.width}
    >
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <span
          {...attributes}
          {...listeners}
          className="text-sm font-medium truncate cursor-grab active:cursor-grabbing flex-1"
          title={item.display_name}
        >
          {item.display_name}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive shrink-0"
          onClick={() => onRemove(item.widget_id)}
          aria-label={`Quitar ${item.display_name} del dashboard`}
        >
          ✕
        </Button>
      </div>
      <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground p-4">
        <WidgetPreview widgetId={item.widget_id} />
      </div>
    </div>
  );
}

function WidgetPreview({ widgetId }: { widgetId: string }) {
  // Placeholder para la rehidratación completa (US4/Q5).
  // En una iteración futura: fetch del spec_json y re-ejecución de la query.
  return (
    <div className="text-center">
      <p className="text-muted-foreground text-xs">Vista previa no disponible</p>
      <p className="text-muted-foreground/60 text-[10px] mt-1">{widgetId}</p>
    </div>
  );
}
