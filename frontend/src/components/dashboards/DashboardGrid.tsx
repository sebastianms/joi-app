"use client";

import {
  DndContext,
  DragEndEvent,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { SortableContext, rectSortingStrategy } from "@dnd-kit/sortable";
import { DashboardItem } from "./DashboardItem";
import type { DashboardItem as DashboardItemType, LayoutItemUpdate } from "@/hooks/useDashboards";

interface DashboardGridProps {
  items: DashboardItemType[];
  onLayoutChange: (updates: LayoutItemUpdate[]) => void;
  onRemoveItem: (widgetId: string) => void;
}

export function DashboardGrid({ items, onLayoutChange, onRemoveItem }: DashboardGridProps) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = items.findIndex((i) => i.widget_id === active.id);
    const newIndex = items.findIndex((i) => i.widget_id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    // Swap grid_y positions between the two items
    const reordered = [...items];
    const draggedY = reordered[oldIndex].grid_y;
    reordered[oldIndex] = { ...reordered[oldIndex], grid_y: reordered[newIndex].grid_y };
    reordered[newIndex] = { ...reordered[newIndex], grid_y: draggedY };

    onLayoutChange(
      reordered.map((item) => ({
        widget_id: item.widget_id,
        grid_x: item.grid_x,
        grid_y: item.grid_y,
        width: item.width,
        height: item.height,
        z_order: item.z_order,
      })),
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-muted-foreground border-2 border-dashed border-border rounded-lg">
        Añade widgets desde tus colecciones para componer el dashboard.
      </div>
    );
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={items.map((i) => i.widget_id)} strategy={rectSortingStrategy}>
        <div
          className="grid gap-3"
          style={{ gridTemplateColumns: "repeat(12, minmax(0, 1fr))" }}
          data-role="dashboard-grid"
        >
          {items.map((item) => (
            <DashboardItem key={item.widget_id} item={item} onRemove={onRemoveItem} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}
