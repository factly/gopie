"use client";

import { PASSWORD_RULES } from "@/lib/validation/password";
import { Check, X } from "lucide-react";

interface PasswordRulesProps {
  password: string;
}

export function PasswordRules({ password }: PasswordRulesProps) {
  if (!password) return null;

  return (
    <ul className="space-y-1 mt-1">
      {PASSWORD_RULES.map((rule) => {
        const passing = rule.test(password);
        return (
          <li key={rule.label} className={`flex items-center gap-1.5 text-xs ${passing ? "text-green-600" : "text-muted-foreground"}`}>
            {passing ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
            {rule.label}
          </li>
        );
      })}
    </ul>
  );
}
