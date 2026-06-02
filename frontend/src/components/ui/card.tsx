import * as React from "react";
import { cn } from "../../services/cn"; // Small helper we will define next or inline here

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glowColor?: "emerald" | "rose" | "indigo" | "none";
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, glowColor = "none", ...props }, ref) => {
    let glowClass = "";
    if (glowColor === "emerald") glowClass = "glow-border-emerald";
    else if (glowColor === "rose") glowClass = "glow-border-rose";
    else if (glowColor === "indigo") glowClass = "glow-border-indigo";

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-xl glass-panel shadow-sm text-zinc-100 transition-all duration-300",
          glowClass,
          className
        )}
        {...props}
      />
    );
  }
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-5 border-b border-zinc-800", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "font-semibold leading-none tracking-tight font-sans text-lg text-zinc-100",
      className
    )}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-xs text-zinc-400 font-sans", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-5 pt-4", className)} {...props} />
));
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-5 pt-0 border-t border-zinc-800", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";
