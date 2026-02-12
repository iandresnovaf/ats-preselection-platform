import React, { useState, useRef, KeyboardEvent } from "react";
import { X } from "lucide-react";
import { Input } from "./input";
import { Badge } from "./badge";

interface TagsInputProps {
  tags: string[];
  onTagsChange: (tags: string[]) => void;
  placeholder?: string;
  maxTags?: number;
  disabled?: boolean;
  className?: string;
  id?: string;
}

export function TagsInput({
  tags,
  onTagsChange,
  placeholder = "Añade skills y presiona Enter...",
  maxTags = 20,
  disabled = false,
  className = "",
  id,
}: TagsInputProps) {
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTag();
    } else if (e.key === "Backspace" && !inputValue && tags.length > 0) {
      removeTag(tags.length - 1);
    }
  };

  const addTag = () => {
    const trimmedValue = inputValue.trim().toLowerCase();
    if (trimmedValue && !tags.includes(trimmedValue) && tags.length < maxTags) {
      onTagsChange([...tags, trimmedValue]);
      setInputValue("");
    }
  };

  const removeTag = (index: number) => {
    if (disabled) return;
    const newTags = tags.filter((_, i) => i !== index);
    onTagsChange(newTags);
  };

  const handleBlur = () => {
    if (inputValue.trim()) {
      addTag();
    }
  };

  return (
    <div
      className={`flex flex-wrap items-center gap-2 p-2 border rounded-md bg-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 ${
        disabled ? "opacity-50 cursor-not-allowed" : ""
      } ${className}`}
      onClick={() => inputRef.current?.focus()}
      role="listbox"
      aria-label="Tags input"
      id={id}
    >
      {tags.map((tag, index) => (
        <Badge
          key={`${tag}-${index}`}
          variant="secondary"
          className="flex items-center gap-1 px-2 py-1"
          role="option"
          aria-selected="true"
        >
          {tag}
          {!disabled && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                removeTag(index);
              }}
              className="ml-1 rounded-full hover:bg-secondary-foreground/20 p-0.5"
              aria-label={`Remove ${tag}`}
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </Badge>
      ))}
      <Input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={tags.length === 0 ? placeholder : ""}
        disabled={disabled || tags.length >= maxTags}
        className="flex-1 min-w-[120px] border-0 focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-7"
        aria-label="Add new tag"
      />
    </div>
  );
}
