import api from "@/services/api";
import {
  PipelineTemplate,
  PipelineStage,
  PipelineStageRule,
  CreatePipelineTemplateData,
  UpdatePipelineTemplateData,
} from "@/types/rhtools";

export const pipelineService = {
  // Templates
  async getTemplates(): Promise<PipelineTemplate[]> {
    const response = await api.get("/rhtools/pipeline-templates");
    return response.data.items || response.data || [];
  },

  async getTemplate(id: string): Promise<PipelineTemplate> {
    const response = await api.get(`/rhtools/pipeline-templates/${id}`);
    return response.data;
  },

  async createTemplate(data: CreatePipelineTemplateData): Promise<PipelineTemplate> {
    const response = await api.post("/rhtools/pipeline-templates", data);
    return response.data;
  },

  async updateTemplate(id: string, data: UpdatePipelineTemplateData): Promise<PipelineTemplate> {
    const response = await api.patch(`/rhtools/pipeline-templates/${id}`, data);
    return response.data;
  },

  async deleteTemplate(id: string): Promise<void> {
    await api.delete(`/rhtools/pipeline-templates/${id}`);
  },

  async setDefaultTemplate(id: string): Promise<void> {
    await api.post(`/rhtools/pipeline-templates/${id}/set-default`);
  },

  // Stages
  async getStages(templateId: string): Promise<PipelineStage[]> {
    const response = await api.get(`/rhtools/pipeline-templates/${templateId}/stages`);
    return response.data;
  },

  async createStage(templateId: string, stage: Omit<PipelineStage, "id" | "template_id" | "created_at" | "updated_at">): Promise<PipelineStage> {
    const response = await api.post(`/rhtools/pipeline-templates/${templateId}/stages`, stage);
    return response.data;
  },

  async updateStage(templateId: string, stageId: string, stage: Partial<PipelineStage>): Promise<PipelineStage> {
    const response = await api.patch(`/rhtools/pipeline-templates/${templateId}/stages/${stageId}`, stage);
    return response.data;
  },

  async deleteStage(templateId: string, stageId: string): Promise<void> {
    await api.delete(`/rhtools/pipeline-templates/${templateId}/stages/${stageId}`);
  },

  async reorderStages(templateId: string, stageIds: string[]): Promise<void> {
    await api.post(`/rhtools/pipeline-templates/${templateId}/reorder-stages`, { stage_ids: stageIds });
  },

  // Rules
  async getStageRules(templateId: string, stageId: string): Promise<PipelineStageRule[]> {
    const response = await api.get(`/rhtools/pipeline-templates/${templateId}/stages/${stageId}/rules`);
    return response.data;
  },

  async addStageRule(templateId: string, stageId: string, rule: Omit<PipelineStageRule, "id" | "stage_id" | "created_at">): Promise<PipelineStageRule> {
    const response = await api.post(`/rhtools/pipeline-templates/${templateId}/stages/${stageId}/rules`, rule);
    return response.data;
  },

  async updateStageRule(templateId: string, stageId: string, ruleId: string, rule: Partial<PipelineStageRule>): Promise<PipelineStageRule> {
    const response = await api.patch(`/rhtools/pipeline-templates/${templateId}/stages/${stageId}/rules/${ruleId}`, rule);
    return response.data;
  },

  async deleteStageRule(templateId: string, stageId: string, ruleId: string): Promise<void> {
    await api.delete(`/rhtools/pipeline-templates/${templateId}/stages/${stageId}/rules/${ruleId}`);
  },
};
