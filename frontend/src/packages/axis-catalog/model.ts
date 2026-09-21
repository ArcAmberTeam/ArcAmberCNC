export interface MenuItem {
  id: string;
  label: string;
  shortcut?: string;
  kind?: 'separator' | 'check' | 'radio';
  group?: string;
  value?: string;
  children?: MenuItem[];
}

export interface ToolbarItem {
  id: string;
  label: string;
  icon: string;
  separator?: boolean;
}
