"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCreateCandidate, useUploadDocument } from "@/hooks/use-headhunting";
import { ArrowLeft, Plus, Trash2, Upload, FileText, Loader2, Briefcase, GraduationCap, User } from "lucide-react";
import Link from "next/link";

interface Experience {
  id: string;
  company: string;
  position: string;
  location: string;
  start_date: string;
  end_date: string;
  current: boolean;
  description: string;
}

interface Education {
  id: string;
  institution: string;
  degree: string;
  field_of_study: string;
  location: string;
  start_date: string;
  end_date: string;
  current: boolean;
}

interface Skill {
  id: string;
  name: string;
  level: "beginner" | "intermediate" | "advanced" | "expert";
}

export default function NewCandidatePage() {
  const router = useRouter();
  const createCandidate = useCreateCandidate();
  const uploadDocument = useUploadDocument();
  const [activeTab, setActiveTab] = useState("manual");
  const [isUploading, setIsUploading] = useState(false);
  
  // Basic info
  const [formData, setFormData] = useState({
    full_name: "",
    national_id: "",
    email: "",
    phone: "",
    location: "",
    linkedin_url: "",
    portfolio_url: "",
    desired_salary: "",
    availability: "immediate",
    summary: "",
  });

  // Dynamic arrays
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [education, setEducation] = useState<Education[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);

  // Add experience
  const addExperience = () => {
    setExperiences([...experiences, {
      id: Date.now().toString(),
      company: "",
      position: "",
      location: "",
      start_date: "",
      end_date: "",
      current: false,
      description: "",
    }]);
  };

  // Update experience
  const updateExperience = (id: string, field: keyof Experience, value: any) => {
    setExperiences(experiences.map(exp => 
      exp.id === id ? { ...exp, [field]: value } : exp
    ));
  };

  // Remove experience
  const removeExperience = (id: string) => {
    setExperiences(experiences.filter(exp => exp.id !== id));
  };

  // Add education
  const addEducation = () => {
    setEducation([...education, {
      id: Date.now().toString(),
      institution: "",
      degree: "",
      field_of_study: "",
      location: "",
      start_date: "",
      end_date: "",
      current: false,
    }]);
  };

  // Update education
  const updateEducation = (id: string, field: keyof Education, value: any) => {
    setEducation(education.map(edu => 
      edu.id === id ? { ...edu, [field]: value } : edu
    ));
  };

  // Remove education
  const removeEducation = (id: string) => {
    setEducation(education.filter(edu => edu.id !== id));
  };

  // Add skill
  const addSkill = () => {
    setSkills([...skills, {
      id: Date.now().toString(),
      name: "",
      level: "intermediate",
    }]);
  };

  // Update skill
  const updateSkill = (id: string, field: keyof Skill, value: any) => {
    setSkills(skills.map(skill => 
      skill.id === id ? { ...skill, [field]: value } : skill
    ));
  };

  // Remove skill
  const removeSkill = (id: string) => {
    setSkills(skills.filter(skill => skill.id !== id));
  };

  // Handle file upload
  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("doc_type", "cv");

      const result = await uploadDocument.mutateAsync({
        file,
        type: "cv",
        applicationId: "temp",
      });

      // If extraction returned data, populate form
      if (result?.extracted_data) {
        const data = result.extracted_data;
        setFormData(prev => ({
          ...prev,
          full_name: data.full_name || prev.full_name,
          email: data.email || prev.email,
          phone: data.phone || prev.phone,
          location: data.location || prev.location,
          linkedin_url: data.linkedin_url || prev.linkedin_url,
          summary: data.summary || prev.summary,
        }));

        if (data.experiences) {
          setExperiences(data.experiences.map((exp: any, idx: number) => ({
            id: Date.now().toString() + idx,
            ...exp,
          })));
        }

        if (data.education) {
          setEducation(data.education.map((edu: any, idx: number) => ({
            id: Date.now().toString() + idx,
            ...edu,
          })));
        }

        if (data.skills) {
          setSkills(data.skills.map((skill: any, idx: number) => ({
            id: Date.now().toString() + idx,
            name: typeof skill === "string" ? skill : skill.name,
            level: skill.level || "intermediate",
          })));
        }

        setActiveTab("manual");
      }
    } catch (error) {
      console.error("Error uploading file:", error);
    } finally {
      setIsUploading(false);
    }
  }, [uploadDocument]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        experiences: experiences.filter(e => e.company && e.position),
        education: education.filter(e => e.institution && e.degree),
        skills: skills.filter(s => s.name),
      };
      
      await createCandidate.mutateAsync(payload);
      router.push("/candidates");
    } catch (error) {
      console.error("Error creating candidate:", error);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-5xl">
      <div className="mb-6">
        <Link
          href="/candidates"
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Volver a candidatos
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2">
            <User className="w-6 h-6" />
            Nuevo Candidato
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="manual" className="flex items-center gap-2">
                <User className="w-4 h-4" />
                Manual
              </TabsTrigger>
              <TabsTrigger value="upload" className="flex items-center gap-2">
                <Upload className="w-4 h-4" />
                Subir CV (PDF/Word)
              </TabsTrigger>
            </TabsList>

            <TabsContent value="upload">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
                <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <h3 className="text-lg font-medium mb-2">
                  Sube un CV en PDF o Word
                </h3>
                <p className="text-gray-500 mb-4">
                  Extraeremos automáticamente la información del candidato
                </p>
                <div className="flex justify-center gap-4">
                  <Label
                    htmlFor="cv-upload"
                    className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    {isUploading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Procesando...
                      </>
                    ) : (
                      <>
                        <FileText className="w-4 h-4" />
                        Seleccionar archivo
                      </>
                    )}
                  </Label>
                  <Input
                    id="cv-upload"
                    type="file"
                    accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    className="hidden"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-4">
                  Formatos soportados: PDF, DOC, DOCX
                </p>
              </div>
            </TabsContent>

            <TabsContent value="manual">
              <form onSubmit={handleSubmit} className="space-y-8">
                {/* Información Básica */}
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <User className="w-5 h-5" />
                    Información Básica
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="full_name">Nombre Completo *</Label>
                      <Input
                        id="full_name"
                        placeholder="Ej: Juan Carlos Martínez"
                        value={formData.full_name}
                        onChange={(e) =>
                          setFormData({ ...formData, full_name: e.target.value })
                        }
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="national_id">Documento de Identidad</Label>
                      <Input
                        id="national_id"
                        placeholder="Ej: 1012345678"
                        value={formData.national_id}
                        onChange={(e) =>
                          setFormData({ ...formData, national_id: e.target.value })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="email">Email</Label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="Ej: juan.martinez@email.com"
                        value={formData.email}
                        onChange={(e) =>
                          setFormData({ ...formData, email: e.target.value })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="phone">Teléfono</Label>
                      <Input
                        id="phone"
                        placeholder="Ej: +57 300 123 4567"
                        value={formData.phone}
                        onChange={(e) =>
                          setFormData({ ...formData, phone: e.target.value })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="location">Ubicación</Label>
                      <Input
                        id="location"
                        placeholder="Ej: Bogotá, Colombia"
                        value={formData.location}
                        onChange={(e) =>
                          setFormData({ ...formData, location: e.target.value })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="linkedin_url">LinkedIn</Label>
                      <Input
                        id="linkedin_url"
                        placeholder="https://linkedin.com/in/..."
                        value={formData.linkedin_url}
                        onChange={(e) =>
                          setFormData({ ...formData, linkedin_url: e.target.value })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="portfolio_url">Portafolio / Website</Label>
                      <Input
                        id="portfolio_url"
                        placeholder="https://..."
                        value={formData.portfolio_url}
                        onChange={(e) =>
                          setFormData({ ...formData, portfolio_url: e.target.value })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="desired_salary">Expectativa Salarial</Label>
                      <Input
                        id="desired_salary"
                        placeholder="Ej: $5,000,000 COP"
                        value={formData.desired_salary}
                        onChange={(e) =>
                          setFormData({ ...formData, desired_salary: e.target.value })
                        }
                      />
                    </div>
                  </div>

                  <div className="space-y-2 mt-4">
                    <Label htmlFor="summary">Resumen Profesional</Label>
                    <Textarea
                      id="summary"
                      placeholder="Breve descripción del perfil del candidato..."
                      rows={4}
                      value={formData.summary}
                      onChange={(e) =>
                        setFormData({ ...formData, summary: e.target.value })
                      }
                    />
                  </div>
                </div>

                {/* Experiencia Laboral */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <Briefcase className="w-5 h-5" />
                      Experiencia Laboral
                    </h3>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addExperience}
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Agregar Experiencia
                    </Button>
                  </div>

                  {experiences.length === 0 && (
                    <p className="text-gray-500 text-sm mb-4">
                      No has agregado experiencia laboral. Haz clic en "Agregar Experiencia" para comenzar.
                    </p>
                  )}

                  <div className="space-y-4">
                    {experiences.map((exp, index) => (
                      <Card key={exp.id} className="bg-gray-50">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="font-medium">Experiencia {index + 1}</h4>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => removeExperience(exp.id)}
                              className="text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Empresa</Label>
                              <Input
                                placeholder="Nombre de la empresa"
                                value={exp.company}
                                onChange={(e) => updateExperience(exp.id, "company", e.target.value)}
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Cargo</Label>
                              <Input
                                placeholder="Título del puesto"
                                value={exp.position}
                                onChange={(e) => updateExperience(exp.id, "position", e.target.value)}
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Ubicación</Label>
                              <Input
                                placeholder="Ciudad, País"
                                value={exp.location}
                                onChange={(e) => updateExperience(exp.id, "location", e.target.value)}
                              />
                            </div>
                            <div className="space-y-2 flex items-center gap-2">
                              <Label className="flex items-center gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={exp.current}
                                  onChange={(e) => updateExperience(exp.id, "current", e.target.checked)}
                                  className="rounded"
                                />
                                Empleo actual
                              </Label>
                            </div>
                            <div className="space-y-2">
                              <Label>Fecha Inicio</Label>
                              <Input
                                type="month"
                                value={exp.start_date}
                                onChange={(e) => updateExperience(exp.id, "start_date", e.target.value)}
                              />
                            </div>
                            {!exp.current && (
                              <div className="space-y-2">
                                <Label>Fecha Fin</Label>
                                <Input
                                  type="month"
                                  value={exp.end_date}
                                  onChange={(e) => updateExperience(exp.id, "end_date", e.target.value)}
                                />
                              </div>
                            )}
                            <div className="col-span-full space-y-2">
                              <Label>Descripción</Label>
                              <Textarea
                                placeholder="Descripción de funciones y logros..."
                                rows={3}
                                value={exp.description}
                                onChange={(e) => updateExperience(exp.id, "description", e.target.value)}
                              />
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>

                {/* Educación */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <GraduationCap className="w-5 h-5" />
                      Educación
                    </h3>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addEducation}
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Agregar Educación
                    </Button>
                  </div>

                  {education.length === 0 && (
                    <p className="text-gray-500 text-sm mb-4">
                      No has agregado educación. Haz clic en "Agregar Educación" para comenzar.
                    </p>
                  )}

                  <div className="space-y-4">
                    {education.map((edu, index) => (
                      <Card key={edu.id} className="bg-gray-50">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="font-medium">Educación {index + 1}</h4>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => removeEducation(edu.id)}
                              className="text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Institución</Label>
                              <Input
                                placeholder="Nombre de la universidad/institución"
                                value={edu.institution}
                                onChange={(e) => updateEducation(edu.id, "institution", e.target.value)}
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Título / Grado</Label>
                              <Input
                                placeholder="Ej: Ingeniero de Sistemas"
                                value={edu.degree}
                                onChange={(e) => updateEducation(edu.id, "degree", e.target.value)}
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Campo de Estudio</Label>
                              <Input
                                placeholder="Ej: Ingeniería"
                                value={edu.field_of_study}
                                onChange={(e) => updateEducation(edu.id, "field_of_study", e.target.value)}
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Ubicación</Label>
                              <Input
                                placeholder="Ciudad, País"
                                value={edu.location}
                                onChange={(e) => updateEducation(edu.id, "location", e.target.value)}
                              />
                            </div>
                            <div className="space-y-2 flex items-center gap-2">
                              <Label className="flex items-center gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={edu.current}
                                  onChange={(e) => updateEducation(edu.id, "current", e.target.checked)}
                                  className="rounded"
                                />
                                Estudiando actualmente
                              </Label>
                            </div>
                            <div className="space-y-2">
                              <Label>Fecha Inicio</Label>
                              <Input
                                type="month"
                                value={edu.start_date}
                                onChange={(e) => updateEducation(edu.id, "start_date", e.target.value)}
                              />
                            </div>
                            {!edu.current && (
                              <div className="space-y-2">
                                <Label>Fecha Fin</Label>
                                <Input
                                  type="month"
                                  value={edu.end_date}
                                  onChange={(e) => updateEducation(edu.id, "end_date", e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>

                {/* Skills */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold">Habilidades</h3>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addSkill}
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Agregar Habilidad
                    </Button>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    {skills.map((skill) => (
                      <div key={skill.id} className="flex items-center gap-2 bg-gray-100 rounded-lg p-2">
                        <Input
                          placeholder="Nombre de la habilidad"
                          value={skill.name}
                          onChange={(e) => updateSkill(skill.id, "name", e.target.value)}
                          className="w-40 border-0 bg-transparent focus-visible:ring-0"
                        />
                        <select
                          value={skill.level}
                          onChange={(e) => updateSkill(skill.id, "level", e.target.value)}
                          className="text-sm border-0 bg-transparent focus:ring-0"
                        >
                          <option value="beginner">Básico</option>
                          <option value="intermediate">Intermedio</option>
                          <option value="advanced">Avanzado</option>
                          <option value="expert">Experto</option>
                        </select>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeSkill(skill.id)}
                          className="text-red-600 h-auto p-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>

                  {skills.length === 0 && (
                    <p className="text-gray-500 text-sm mt-2">
                      No has agregado habilidades.
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-4 pt-6 border-t">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => router.push("/candidates")}
                  >
                    Cancelar
                  </Button>
                  <Button
                    type="submit"
                    disabled={createCandidate.isPending || !formData.full_name}
                    className="px-8"
                  >
                    {createCandidate.isPending ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Creando...
                      </>
                    ) : (
                      "Crear Candidato"
                    )}
                  </Button>
                </div>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
