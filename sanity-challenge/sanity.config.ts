import {defineConfig} from 'sanity'
import {structureTool} from 'sanity/structure'
import {visionTool} from '@sanity/vision'
import {schemaTypes} from './schemaTypes'

export default defineConfig({
  name:'supreme_computation_totality', title:'Supreme Computation — Totality Evidence Plane',
  projectId: process.env.SANITY_STUDIO_PROJECT_ID || 'nofw4k8i',
  dataset: process.env.SANITY_STUDIO_DATASET || 'production',
  plugins:[structureTool(),visionTool()], schema:{types:schemaTypes}
})
