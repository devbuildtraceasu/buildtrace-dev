import { cn } from "@/lib/utils";

interface StepperProps {
  currentStep: number;
  steps: string[];
  className?: string;
}

export default function Stepper({ currentStep, steps, className }: StepperProps) {
  return (
    <div className={cn("flex items-center justify-center", className)} data-testid="stepper">
      <div className="flex items-center space-x-4">
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const isActive = stepNumber === currentStep;
          const isCompleted = stepNumber < currentStep;
          const isLast = index === steps.length - 1;

          return (
            <div key={step} className="flex items-center">
              <div className="flex items-center">
                <div
                  className={cn(
                    "w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-colors",
                    {
                      "stepper-active": isActive,
                      "stepper-completed": isCompleted,
                      "bg-gray-300 text-gray-600": !isActive && !isCompleted,
                    }
                  )}
                  data-testid={`step-${stepNumber}`}
                >
                  {isCompleted ? (
                    <span>✓</span>
                  ) : (
                    stepNumber
                  )}
                </div>
                <span
                  className={cn(
                    "ml-3 text-sm font-medium transition-colors",
                    {
                      "text-gray-900": isActive || isCompleted,
                      "text-gray-500": !isActive && !isCompleted,
                    }
                  )}
                  data-testid={`step-label-${stepNumber}`}
                >
                  {step}
                </span>
              </div>
              {!isLast && (
                <div
                  className={cn(
                    "w-16 h-0.5 ml-4 transition-colors",
                    {
                      "bg-primary": isCompleted,
                      "bg-gray-300": !isCompleted,
                    }
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
