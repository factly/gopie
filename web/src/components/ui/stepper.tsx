"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { CheckCircle2, Circle } from "lucide-react";

export interface Step {
  id: string;
  title: string;
  description?: string;
}

export interface StepperProps {
  steps: Step[];
  currentStep: number;
  className?: string;
}

export function Stepper({ steps, currentStep, className }: StepperProps) {
  return (
    <div className={cn("w-full", className)}>
      <nav aria-label="Progress">
        <ol className="flex items-center justify-between">
          {steps.map((step, index) => {
            const stepNumber = index + 1;
            const isCompleted = stepNumber < currentStep;
            const isCurrent = stepNumber === currentStep;
            const isUpcoming = stepNumber > currentStep;

            return (
              <li key={step.id} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  {/* Step indicator */}
                  <div className="flex items-center">
                    <div
                      className={cn(
                        "flex items-center justify-center w-8 h-8 rounded-full border-2 transition-colors",
                        {
                          "bg-primary border-primary text-primary-foreground": isCompleted,
                          "border-primary text-primary bg-background": isCurrent,
                          "border-muted-foreground/30 text-muted-foreground bg-background": isUpcoming,
                        }
                      )}
                    >
                      {isCompleted ? (
                        <CheckCircle2 className="w-5 h-5" />
                      ) : (
                        <span className="text-sm font-medium">{stepNumber}</span>
                      )}
                    </div>
                  </div>

                  {/* Step content */}
                  <div className="mt-2 text-center">
                    <div
                      className={cn(
                        "text-sm font-medium transition-colors",
                        {
                          "text-primary": isCompleted || isCurrent,
                          "text-muted-foreground": isUpcoming,
                        }
                      )}
                    >
                      {step.title}
                    </div>
                    {step.description && (
                      <div className="text-xs text-muted-foreground mt-1 max-w-24">
                        {step.description}
                      </div>
                    )}
                  </div>
                </div>

                {/* Connector line */}
                {index < steps.length - 1 && (
                  <div
                    className={cn(
                      "flex-1 h-0.5 mx-4 transition-colors",
                      {
                        "bg-primary": stepNumber < currentStep,
                        "bg-muted-foreground/30": stepNumber >= currentStep,
                      }
                    )}
                  />
                )}
              </li>
            );
          })}
        </ol>
      </nav>
    </div>
  );
}

export interface StepperContentProps {
  children: React.ReactNode;
  className?: string;
}

export function StepperContent({ children, className }: StepperContentProps) {
  return (
    <div className={cn("mt-8", className)}>
      {children}
    </div>
  );
}

export interface StepperActionsProps {
  children: React.ReactNode;
  className?: string;
}

export function StepperActions({ children, className }: StepperActionsProps) {
  return (
    <div className={cn("flex justify-between mt-8", className)}>
      {children}
    </div>
  );
}
