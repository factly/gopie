import sgMail from "@sendgrid/mail";

// Initialize SendGrid with API key
const apiKey = process.env.SENDGRID_API_KEY;
if (apiKey) {
  sgMail.setApiKey(apiKey);
}

// SendGrid Dynamic Template IDs
const templates = {
  emailVerification: process.env.SENDGRID_TEMPLATE_EMAIL_VERIFICATION || "",
  passwordReset: process.env.SENDGRID_TEMPLATE_PASSWORD_RESET || "",
  organizationInvitation: process.env.SENDGRID_TEMPLATE_INVITATION || "",
};

// Default sender email
const defaultFrom = {
  email: "gopie@factly.in",
  name: "GoPie",
};

interface SendEmailOptions {
  to: string;
  templateId: string;
  dynamicTemplateData: Record<string, string | number | boolean | undefined>;
}

/**
 * Send an email using SendGrid dynamic templates
 */
async function sendEmail({ to, templateId, dynamicTemplateData }: SendEmailOptions): Promise<void> {
  if (!apiKey) {
    console.warn("[Email] SendGrid API key not configured, skipping email send");
    return;
  }

  if (!templateId) {
    console.warn("[Email] Template ID not configured, skipping email send");
    return;
  }

  const msg = {
    to,
    from: defaultFrom,
    templateId,
    dynamicTemplateData,
  };

  try {
    await sgMail.send(msg);
  } catch (error: unknown) {
    // Extract detailed error information from SendGrid response
    if (error && typeof error === "object" && "response" in error) {
      const sgError = error as { response?: { body?: { errors?: Array<{ message: string }> } } };
      const errors = sgError.response?.body?.errors;
      if (errors && errors.length > 0) {
        console.error("[Email] SendGrid error details:", errors.map(e => e.message).join(", "));
      }
    }
    console.error("[Email] Failed to send email:", error);
    throw error;
  }
}

/**
 * Send email verification email
 */
export async function sendVerificationEmail(params: {
  email: string;
  verificationUrl: string;
  token: string;
}): Promise<void> {
  const { email, verificationUrl, token } = params;

  await sendEmail({
    to: email,
    templateId: templates.emailVerification,
    dynamicTemplateData: {
      verification_url: verificationUrl,
      token,
    },
  });
}

/**
 * Send password reset email
 */
export async function sendPasswordResetEmail(params: {
  email: string;
  resetUrl: string;
  token: string;
}): Promise<void> {
  const { email, resetUrl, token } = params;

  await sendEmail({
    to: email,
    templateId: templates.passwordReset,
    dynamicTemplateData: {
      reset_url: resetUrl,
      token,
    },
  });
}

/**
 * Send organization invitation email
 */
export async function sendInvitationEmail(params: {
  email: string;
  inviterName: string;
  organizationName: string;
  invitationUrl: string;
}): Promise<void> {
  const { email, inviterName, organizationName, invitationUrl } = params;

  await sendEmail({
    to: email,
    templateId: templates.organizationInvitation,
    dynamicTemplateData: {
      inviter_name: inviterName,
      organization_name: organizationName,
      invitation_url: invitationUrl,
    },
  });
}

/**
 * Check if email sending is configured
 */
export function isEmailConfigured(): boolean {
  return Boolean(apiKey);
}

/**
 * Check if a specific template is configured
 */
export function isTemplateConfigured(template: keyof typeof templates): boolean {
  return Boolean(templates[template]);
}
