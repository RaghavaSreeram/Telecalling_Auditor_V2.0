import React from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

/**
 * Safe Select wrapper that prevents ResizeObserver loops
 * Uses portal mounting and debounced callbacks
 */
export const SafeSelect = ({ 
  value, 
  onValueChange, 
  children, 
  placeholder,
  testId,
  ...props 
}) => {
  const [isOpen, setIsOpen] = React.useState(false);
  
  const handleValueChange = React.useCallback((newValue) => {
    // Use requestAnimationFrame to defer state update
    requestAnimationFrame(() => {
      onValueChange?.(newValue);
      setIsOpen(false);
    });
  }, [onValueChange]);

  const handleOpenChange = React.useCallback((open) => {
    requestAnimationFrame(() => {
      setIsOpen(open);
    });
  }, []);

  return (
    <Select 
      value={value} 
      onValueChange={handleValueChange}
      open={isOpen}
      onOpenChange={handleOpenChange}
      {...props}
    >
      <SelectTrigger data-testid={testId}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {children}
      </SelectContent>
    </Select>
  );
};

export const SafeSelectItem = SelectItem;
