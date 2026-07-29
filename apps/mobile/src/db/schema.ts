import { Database } from '@nozbe/watermelondb';
import SQLiteAdapter from '@nozbe/watermelondb/adapters/sqlite';
import { appSchema, tableSchema } from '@nozbe/watermelondb';

export const schema = appSchema({
  version: 1,
  tables: [
    tableSchema({
      name: 'diagnosis_queue',
      columns: [
        { name: 'image_path',   type: 'string' },
        { name: 'animal_type',  type: 'string', isOptional: true },
        { name: 'crop_type',    type: 'string', isOptional: true },
        { name: 'confidence',   type: 'number' },
        { name: 'synced',       type: 'boolean' },
        { name: 'created_at',   type: 'number' },
      ],
    }),
    tableSchema({
      name: 'livestock_profiles',
      columns: [
        { name: 'name',         type: 'string' },
        { name: 'type',         type: 'string' },
        { name: 'breed',        type: 'string', isOptional: true },
        { name: 'tag_number',   type: 'string', isOptional: true },
        { name: 'health_status',type: 'string' },
        { name: 'updated_at',   type: 'number' },
      ],
    }),
  ],
});

const adapter = new SQLiteAdapter({ schema, jsi: true });
export const database = new Database({ adapter, modelClasses: [] });
